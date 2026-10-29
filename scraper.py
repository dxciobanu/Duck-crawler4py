import re
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs
from bs4 import BeautifulSoup
from stats import record_page

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    # only allow successful responses, status of 200 means it's successful
    if resp.status != 200:
        return []

    if resp.raw_response is None:
        return []

    # retrieve the contents of the webpage and prevent processing large pages (like 10 MB)
    content = resp.raw_response.content

    # ignore empty pages
    if not content:
        return []

    if len(content) > 10 * 1024 * 1024:
        return []

    # check the content type and avoid parsing non-HTML content
    content_type = resp.raw_response.headers.get("Content-Type", "").lower()
    if content_type and "text/html" not in content_type:
        return []

    # use final response url
    baseURL = resp.raw_response.url or resp.url or url

    # reject pages redirected outside allowed
    if not is_valid(baseURL):
        return []

    # parse the html
    soup = BeautifulSoup(content, "html.parser")
    links = []
    seen = set()

    # extracting the hyperlinks
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href:
            continue

        try:
            # convert to absolute urls
            absURL = urljoin(baseURL, href)

            # remove url fragments
            absURL, fragment = urldefrag(absURL)

        except (TypeError, ValueError):
            continue

        # avoid duplicates
        if absURL not in seen:
            seen.add(absURL)
            links.append(absURL)

    # extract text for statistics
    for elem in soup(["script", "style", "noscript"]):
        elem.decompose()

    text = soup.get_text(separator=" ", strip=True)

    # record stat for the page
    record_page(baseURL, text)

    return links

# attempt to avoid traps
def is_trap(url):
    parsed = urlparse(url)
    path = parsed.path.lower()

    # avoid excessively long urls
    if len(url) > 2048:
        return True

    # avoid urls with very long path depths
    segments = [s for s in path.split("/") if s]

    if len(segments) > 12:
        return True

    # avoid repeated path segments
    if len(segments) >= 4:
        for i in range(len(segments) - 3):
            if len(set(segments[i:i + 4])) == 1:
                return True

    # avoid very long query strings
    if len(parsed.query) > 300:
        return True

    # avoid urls with excessive query parameters
    params = parse_qs(parsed.query)
    if len(params) > 10:
        return True

    return False

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        # only crawl the four domains
        allowed = ["ics.uci.edu",
                   "cs.uci.edu",
                   "informatics.uci.edu",
                   "stat.uci.edu"]

        # accepting subdomains of our main domains
        hostname = parsed.hostname
        if hostname is None:
            return False
        if not any (hostname == domain or hostname.endswith("." + domain)
                    for domain in allowed):
            return False

        # rejecting non-ASCII urls
        if not url.isascii():
            return False

        # check if trap
        if is_trap(url):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    # a little confused here, can i change this? don't want crawler to crash if it
    # encounters an url we want to reject
    except (TypeError, ValueError) as e:
        print(f"Invalid URL {url!r}: {e}")
        return False
