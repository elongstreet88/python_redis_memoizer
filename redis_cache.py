from datetime import date, datetime
import json
from multiprocessing import get_logger
from pydantic import BaseModel
import redis

# create a Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return obj.__dict__
        except AttributeError:
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, bytes):
                return obj.decode()
            elif isinstance(obj, BaseModel):
                return obj.dict()
            return super().default(obj)
        
class RedisCache:
    def __init__(self, func, expires_seconds):
        # Store the original function called
        self.func = func

        # Store parameters
        self.expires_seconds = expires_seconds

        # Reserved for the instance of the class if this is a class method to be determined in [__get__]
        self.instance = None

    def __get__(self, instance, owner):
        # Gets the instance of the class if this is a class method
        self.instance = instance

        # Return this decorator
        return self
        
    def __call_original_function(self, args, kwargs):
        # If decorating a class method, pass the instance of the class as the first argument
        if self.instance:
            return self.func(self.instance, *args, **kwargs)
        
        # Otherwise, just call the original function
        return self.func(*args, **kwargs)
    
    def __generate_cache_key(self, args, kwargs):
        # generate a unique signature for the function call
        signature = f"{self.func.__module__}.{self.func.__qualname__}"

        for key, value in kwargs.items():
            signature += f":{key}:{type(value)}:{value}"

        for arg in args:
            signature += f":{type(arg)}:{arg}"

        # hash the signature to generate the cache key
        signature = f"{signature}:{hash(signature)}"
        return signature
    
    def __call__(self, *args, **kwargs):
        """
        Returns the current cache value for the function call
        If the value is not in the cache, it will call the function and cache the result
        """

        # Get cache key
        cache_key = self.__generate_cache_key(args, kwargs)

        # Use cache if its available
        cached_result = redis_client.get(cache_key)
        if cached_result is not None:
            return json.loads(cached_result.decode())

        # if not, call the function and cache the result
        result = self.__call_original_function(args, kwargs)
        redis_client.set(cache_key, json.dumps(result, cls=CustomJSONEncoder), ex=self.expires_seconds)
        return result

    def get_cache_key(self, *args, **kwargs):
        """
        Returns the cache key for the function call but does not call the function
        Example:
            @redis_cache
            def test1(a):
                return 5
                
            print(test1.get_cache_key('hello'))
            # Output: __main__.test1:<class 'str'>:hello:123456789
        """
        key = self.__generate_cache_key(args, kwargs)
        return key
    
    def refresh_cache(self, *args, **kwargs):
        """
        Forces refresh the cache for the function call.
        This does not invalidate the cache, it just updates it after the function has been called.

        Example:
            @redis_cache
            def test1(a):
                return 5

            test1.refresh_cache('hello')
        """

        # Get cache key
        cache_key = self.__generate_cache_key(args, kwargs)

        # Call the function and get the result
        result = self.__call_original_function(args, kwargs)

        # Set the cache
        redis_client.set(cache_key, json.dumps(result, cls=CustomJSONEncoder), ex=self.expires_seconds)

        # Return the result
        return result

def cache(expires_seconds=300):
    """
    Decorator factory, required in order to pass parameters to the decorator including the function
    All future parameters to the decorator must be passed by the factory
    """

    # Create the decorator which instantiates the RedisCache class and passes the function and parameters
    def decorator(func):
         return RedisCache(func, expires_seconds)
    
    # Return the decorator
    return decorator
