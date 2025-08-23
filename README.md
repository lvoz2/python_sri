# python_sri

python_sri is a Python module to generate [Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity) hashes on the fly. It supports Python 3.10+, including [free threading](https://py-free-threading.github.io/), and has **zero dependencies**

## Quickstart

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install python_sri.

```bash
pip install python_sri
```

Then import, setup and hash!

```python
from python_sri import SRI

# Creating an instance, providing your site's domain name and some optional config
# sri = SRI('https://example.com')
# OR
sri = SRI('https://example.com', static={'directory': 'static', 'url_path': '/static'})

@sri.html_uses_sri('/')
def index() -> str:
    return '''
        ...
        <link rel="stylesheet" href="static/main.css" integrity />
        <script src="static/main.js" integity></script>
        ...
    '''
# -> ...
#    <link rel="stylesheet" href="static/main.css" integrity="sha384-HASH">
     <script src="static/main.js" integrity="sha384-HASH"></script>
#    ...

sri.hash_html('/', '<script src="/static/main.js" integrity></script>')
# -> <script src="/static/main.js" integrity="sha384-HASH"></script>
```

## Usage

#### python_sri.SRI(*domain*, \*, *static*=None, *hash_alg*='sha384', *in_dev*=False, *\*\*kwargs*)
Creates the main instance for generating hashes

domain: The domain for the site python_sri is being used for

static: An optional dictionary with a ```directory``` attribute holding a path-like object or string indicating where on the local filesystem static content is loaded from and a ```url_path``` attribute that refers to the path in the URL where static content is loaded from

hash_alg: The hashing algorithm to use, out of 'sha256', 'sha384' and 'sha512'

in_dev: Whether this is a development site, which will create new hashes for each request if True

kwargs: Global overrides to the defaults of python_sri.SRI.hash_url's arguments. Useful for giving arguments to that function for adding SRI hashes to HTML

#### python_sri.SRI.domain
Read only. The domain of the site

#### python_sri.SRI.hash_alg
Read only. The hashing algorithm chosen

#### python_sri.SRI.in_dev
Read only. Whether the site is in development or production

#### python_sri.SRI.clear_cache()
Clear the instance's caches

#### @python_sri.SRI.html_uses_sri(*route*, *clear*=None)
Wrapper around python_sri.SRI.hash_html() to simplify using python_sri

route: The URL path that this function responds to, like "/" or "/index.html"

clear: Whether to run python_sri.SRI.clear_cache() after finishing. By default, this inherits the value of python_sri.SRI.in_dev

#### python_sri.SRI.hash_html(*route*, *html*, *clear*=None) -> str
Parses and returns some HTML, adding in a SRI hash where an ```integrity``` attribute is found. If an error occurs, this function will remove the ```integrity``` attribute and put the error message in a new ```data-sri-error``` attribute instead

Will not add SRI hashes to absolute URLs, and is unlikely to ever do so

route: The URL path that the calling function responds to, like "/" or "/index.html"

html: The html document or fragment to add SRI hashes to

clear: Whether to run python_sri.SRI.clear_cache() after finishing. By default, this inherits the value of python_sri.SRI.in_dev

#### python_sri.SRI.hash_file_path(*path*, *clear*=None) -> str
Creates a SRI hash for the file at ```path```. Raises exceptions upon failures

path: A path-like object to the file to hash

clear: Whether to run python_sri.SRI.clear_cache() after finishing. By default, this inherits the value of python_sri.SRI.in_dev

#### python_sri.SRI.hash_file_object(*file*, *clear*=None) -> str
Creates a SRI hash for the file object passed in the ```file``` argument. This file must be created in binary/buffered mode, ie ```open(path, "rb")```. Attempts to do so otherwise will raise exceptions. In Python 3.10, this is just a wrapper around python_sri.SRI.hash_data(). Will return a hash or raise an exception

file: A file-like object for hashing

clear: Whether to run python_sri.SRI.clear_cache() after finishing. By default, this inherits the value of python_sri.SRI.in_dev

#### python_sri.SRI.hash_url(*url*, *\**, *timeout*=None, *headers*={}, *context*=None, *route*=None, *clear*=None) -> str
Creates a SRI hash for the given URL. **Not reccomended for absolute URLs outside of your control**.

url: The URL of the resource to hash

Keyword Arguments:

timeout: An optional float to set the timeout, which is the time to wait for a response, for the request in seconds. Defaults to the global timeout, which can be set with [```socket.setdefaulttimeout(timeout)```](https://docs.python.org/3/library/socket.html#socket.setdefaulttimeout)

headers: The headers to send with the request. Defaults to ```{}```

context: A ssl.SSLContext or None, which is used to customise the settings for creating a secure connection with SSL/TLS. Defaults to [```ssl.create_default_context()```](https://docs.python.org/3/library/ssl.html#ssl.create_default_context)

route: The route to the page making the request. Mandatory for relative URLs

clear: Whether to run python_sri.SRI.clear_cache() after finishing. By default, this inherits the value of python_sri.SRI.in_dev

#### python_sri.SRI.hash_data(*data*) -> str
Creates a SRI hash for the data in ```data```

data: A bytes-like object containing the data to hash. If attempting to give a string or textual data that is not already bytes-like, use methods like [```str.encode```](https://docs.python.org/3/library/stdtypes.html#str.encode)

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## Todo

- Add support for Django, Flask and FastAPI directly, so that users don't have to use any workarounds to use this module
- Multithread getting resources from the local filesystem or over the network
- Work on documentation, perhaps even use Sphinx or something similar

## License

[MIT](https://choosealicense.com/licenses/mit/)
