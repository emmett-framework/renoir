# -*- coding: utf-8 -*-
"""
    renoir.cache
    ------------

    Provides caching utils.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

import os

from ._shortcuts import hashlib_sha1


def make_hash(value):
    return hashlib_sha1(value).hexdigest()[:10]


class TemplaterCache:
    def __init__(self, templater, reload=False):
        self.templater = templater
        self.changes = reload
        self.load = LoaderCache(self)
        self.prerender = PrerenderCache(self)
        self.parse = ParserCache(self)


class InnerCache:
    def __init__(self, cache_interface):
        self.cache = cache_interface
        self.data = {}
        self._configure()

    def _configure(self):
        self.get = self.reloader_get if self.cache.changes else self.cached_get


class LoaderCache(InnerCache):
    def __init__(self, cache_interface):
        super().__init__(cache_interface)
        self.mtimes = {}

    def reloader_get(self, file_path):
        try:
            mtime = os.stat(file_path).st_mtime
        except Exception:
            return None
        old_time = self.mtimes.get(file_path, 0)
        if mtime > old_time:
            return None
        return self.cached_get(file_path)

    def cached_get(self, file_path):
        return self.data.get(file_path)

    def set(self, file_path, source):
        self.data[file_path] = source
        self.mtimes[file_path] = os.stat(file_path).st_mtime


class HashableCache(InnerCache):
    def __init__(self, cache_interface):
        super().__init__(cache_interface)
        self.hashes = {}

    def reloader_get(self, name, source):
        hashed = make_hash(source)
        if self.hashes.get(name) != hashed:
            return None
        return self.cached_get(name, source)

    def cached_get(self, name, source):
        return self.data.get(name)

    def set(self, name, source):
        self.data[name] = source
        if self.cache.changes:
            self.hashes[name] = make_hash(source)


class PrerenderCache(HashableCache):
    pass


class ParserCache(HashableCache):
    def __init__(self, cache_interface):
        super().__init__(cache_interface)
        self.cdata = {}
        self.dependencies = {}

    def _expired_dependency(self, name):
        path, file_name = self.cache.templater.preload(name)
        file_path = os.path.join(path, file_name)
        if os.stat(file_path).st_mtime != self.cache.load.mtimes[file_path]:
            return True
        return False

    def reloader_get(self, name, source):
        hashed = make_hash(source)
        if self.hashes.get(name) != hashed:
            return None, None
        for dep_name in self.dependencies[name]:
            if self._expired_dependency(dep_name):
                return None, None
        return self.cached_get(name, source)

    def cached_get(self, name, source):
        return self.data.get(name), self.cdata.get(name)

    def set(self, name, source, compiled, content, dependencies):
        self.data[name] = compiled
        self.cdata[name] = content
        if self.cache.changes:
            self.hashes[name] = make_hash(source)
            self.dependencies[name] = dependencies
