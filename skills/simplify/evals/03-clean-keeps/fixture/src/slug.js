// RFC 3986 unreserved characters only: the CDN rejects any other byte in a path segment.
const slug = title => title.toLowerCase().replace(/[^a-z0-9._~-]+/g, "-").replace(/^-+|-+$/g, "");
module.exports = { slug };
