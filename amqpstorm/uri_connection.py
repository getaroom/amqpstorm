"""AMQP-Storm Uri wrapper for Connection."""

import logging

from amqpstorm import compatibility
from amqpstorm.compatibility import ssl
from amqpstorm.compatibility import urlparse
from amqpstorm.connection import Connection

LOGGER = logging.getLogger(__name__)


class UriConnection(Connection):
    """Create a new Connection instance using an AMQP Uri string.

        Usage:
            UriConnect('amqp://guest:guest@localhost:5672/%2F?heartbeat=60')
            UriConnect('amqps://guest:guest@localhost:5671/%2F?heartbeat=60')
    """

    def __init__(self, uri, lazy=False):
        """
        :param str uri: AMQP Connection string

        :raises TypeError: Raises on invalid uri.
        :raises ValueError: Raises on invalid uri.
        :raises AttributeError: Raises on invalid uri.
        :raises AMQPConnectionError: Raises on Connection error.
        """
        uri = compatibility.patch_uri(uri)
        parsed_uri = urlparse.urlparse(uri)
        use_ssl = parsed_uri.scheme == 'https'
        hostname = parsed_uri.hostname or 'localhost'
        port = parsed_uri.port or 5672
        username = urlparse.unquote(parsed_uri.username) or 'guest'
        password = urlparse.unquote(parsed_uri.password) or 'guest'
        kwargs = self._parse_uri_options(parsed_uri, use_ssl, lazy)
        super(UriConnection, self).__init__(hostname, username,
                                            password, port,
                                            **kwargs)

    def _parse_uri_options(self, parsed_uri, use_ssl, lazy):
        """Parse the uri options.

        :param parsed_uri:
        :param bool use_ssl:
        :return:
        """
        kwargs = urlparse.parse_qs(parsed_uri.query)
        options = {
            'ssl': use_ssl,
            'virtual_host': urlparse.unquote(parsed_uri.path[1:]) or '/',
            'heartbeat': int(kwargs.get('heartbeat', [60])[0]),
            'timeout': int(kwargs.get('timeout', [30])[0]),
            'lazy': lazy
        }
        if compatibility.SSL_SUPPORTED and use_ssl:
            options['ssl_options'] = self._parse_ssl_options(kwargs)
        return options

    def _parse_ssl_options(self, ssl_kwargs):
        """Parse SSL Options.

        :param ssl_kwargs:
        :rtype: dict
        """
        ssl_options = {}
        for key in ssl_kwargs:
            if key not in compatibility.SSL_OPTIONS:
                LOGGER.warning('invalid ssl option: %s', key)
                continue
            if 'ssl_version' in key:
                value = self._get_ssl_version(ssl_kwargs[key][0])
            elif 'cert_reqs' in key:
                value = self._get_ssl_validation(ssl_kwargs[key][0])
            else:
                value = ssl_kwargs[key][0]
            ssl_options[key] = value
        return ssl_options

    def _get_ssl_version(self, value):
        """Get the SSL Version.

        :param str value:
        :return: SSL Version
        """
        return self._get_ssl_attribute(value, compatibility.SSL_VERSIONS,
                                       ssl.PROTOCOL_TLSv1,
                                       'ssl_options: ssl_version \'%s\' not '
                                       'found falling back to PROTOCOL_TLSv1.')

    def _get_ssl_validation(self, value):
        """Get the SSL Validation option.

        :param str value:
        :return: SSL Certificate Options
        """
        return self._get_ssl_attribute(value, compatibility.SSL_CERT_MAP,
                                       ssl.CERT_NONE,
                                       'ssl_options: cert_reqs \'%s\' not '
                                       'found falling back to CERT_NONE.')

    @staticmethod
    def _get_ssl_attribute(value, mapping, default_value, warning_message):
        """Get the SSL attribute based on the mapping.

            If no valid attribute can be found, fall-back on default and
            display a warning.

        :param str value:
        :param dict mapping: Dictionary based mapping
        :param default_value: Default fall-back value
        :param str warning_message: Warning message
        :return:
        """
        for key in mapping:
            if not key.endswith(value.lower()):
                continue
            return mapping[key]
        LOGGER.warning(warning_message, value)
        return default_value
