# Python Redis Memoizer
A basic python memoizer that supports class methods and stand alone functions.

# Example Usage

## Initializing
`from redis_cache import cache`

## Cache a function
```
@cache(expires_seconds=300)
def test1(a):
    return 5
test1()
```

## Cache a method
class Test:
    @cache(expires_seconds=300)
    def caclulcate_something(self, a):
        return 5
test = Test()
test.caclulcate_something()

# Refresh the cache
test1.refresh_cache('hello')
