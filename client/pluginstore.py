# -*- coding: utf-8-*-
import os
import re
import logging
import gettext
import ConfigParser as configparser
import pkgutil
import inspect
from . import plugin


MANDATORY_OPTIONS = (
    ('Plugin', 'Name'),
    ('Plugin', 'Version'),
    ('Plugin', 'License')
)
RE_TRANSLATIONS = re.compile(r'^[a-z]{2}(_[A-Z]{2}){0,1}$')


class PluginInfo(object):
    def __init__(self, cp, plugin_class, translations):
        self._cp = cp
        self.plugin_class = plugin_class
        self.translations = translations

    def _get_optional_info(self, *args):
        try:
            value = self._cp.get(*args)
        except configparser.Error:
            value = ''
        return value

    @property
    def name(self):
        return self._cp.get('Plugin', 'Name')

    @property
    def version(self):
        return self._cp.get('Plugin', 'Version')

    @property
    def license(self):
        return self._cp.get('Plugin', 'License')

    @property
    def description(self):
        return self._get_optional_info('Plugin', 'Description')

    @property
    def url(self):
        return self._get_optional_info('Plugin', 'URL')

    @property
    def author_name(self):
        return self._get_optional_info('Author', 'Name')

    @property
    def author_email(self):
        return self._get_optional_info('Author', 'Email')

    @property
    def author_url(self):
        return self._get_optional_info('Author', 'URL')


def get_translations(plugin_directory):
    # Parse Languages
    locale_path = os.path.join(plugin_directory, 'languages')

    translations = {}
    if os.path.isdir(locale_path):
        for content in os.listdir(locale_path):
            if not os.path.isdir(os.path.join(locale_path, content)):
                lang, ext = os.path.splitext(content)
                if ext == (os.extsep + 'mo') and RE_TRANSLATIONS.match(lang):
                    with open(os.path.join(locale_path, content)) as f:
                        translations[lang] = gettext.GNUTranslations(f)
    return translations


def find_plugin_class(plugin_directory, superclasses):
    for finder, name, ispkg in pkgutil.walk_packages([plugin_directory]):
        try:
            loader = finder.find_module(name)
            mod = loader.load_module(name)
        except:
            raise

        plugin_classes = inspect.getmembers(
            mod, lambda cls: inspect.isclass(cls) and
            issubclass(cls, tuple(superclasses)))

        if len(plugin_classes) < 1:
            raise Exception("Not a valid plugin")
        elif len(plugin_classes) > 1:
            raise Exception("Multiple subclasses found")

        return plugin_classes[0][1]


class PluginStore(object):
    def __init__(self, plugin_dirs):
        self._logger = logging.getLogger(__name__)
        self._plugin_dirs = plugin_dirs
        self._plugins = {}
        self._info_fname = os.extsep.join(['plugin', 'info'])
        self._categories_map = {
            'speechhandler': plugin.SpeechHandlerPlugin,
        }

    def detect_plugins(self):
        for plugin_dir in self._plugin_dirs:
            for root, dirs, files in os.walk(plugin_dir, topdown=True):
                for name in files:
                    if name != self._info_fname:
                        continue
                    try:
                        self._logger.debug("Found plugin candidate at: %s",
                                           root)
                        plugin_info = self.parse_plugin(root)
                    except:
                        raise
                    else:
                        self._plugins[plugin_info.name] = plugin_info
                        self._logger.debug("Found valid plugin: %s %s",
                                           plugin_info.name,
                                           plugin_info.version)

    def parse_plugin(self, plugin_directory):
        info_file = os.path.join(plugin_directory, self._info_fname)
        cp = configparser.RawConfigParser()
        cp.read(info_file)

        options_missing = False
        for option in MANDATORY_OPTIONS:
            if not cp.has_option(*option):
                options_missing = True
                print("Missing option", option)

        if options_missing:
            raise Exception("OptionsMissing")

        plugin_class = find_plugin_class(plugin_directory,
                                         self._categories_map.values())

        translations = get_translations(plugin_directory)

        return PluginInfo(cp, plugin_class, translations)

    def get_plugins_by_category(self, category):
        superclass = self._categories_map[category]
        return [info for info in self._plugins.values()
                if issubclass(info.plugin_class, superclass)]
