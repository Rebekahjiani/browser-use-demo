import unittest
from readonly_proxy import allowed, BufferedChannel
from unittest.mock import Mock


class Tests(unittest.TestCase):
    def test_search_and_cart_view_allowed(self):
        for target in ['/catalogsearch/result/?q=shoe', '/catalogsearch/advanced/result/?name=shoe',
                       '/checkout/cart/', '/home-kitchen.html?price=10-20', '/media/catalog/product/a.jpg']:
            self.assertTrue(allowed('GET', target))

    def test_writes_blocked_even_with_get(self):
        for target in ['/checkout/cart/add/product/16', '/wishlist/index/add/product/16',
                       '/customer/account/create/', '/review/product/post/id/16',
                       '/newsletter/subscriber/new', '/checkout/cart/delete/id/1']:
            self.assertFalse(allowed('GET', target))

    def test_post_to_search_blocked(self):
        self.assertFalse(allowed('POST', '/catalogsearch/result/'))

    def test_browser_proxy_only_accepts_benchmark_origin(self):
        self.assertTrue(allowed('GET', 'http://127.0.0.1:7770/catalogsearch/result/?q=shoe'))
        self.assertFalse(allowed('GET', 'https://127.0.0.1:7770/'))
        self.assertFalse(allowed('GET', 'http://127.0.0.1:7771/'))

    def test_http_file_is_buffered_for_complete_chunks(self):
        channel = Mock()
        BufferedChannel(channel).makefile('rb')
        channel.makefile.assert_called_once_with('rb', 65536)

    def test_connection_close_keeps_response_stream_alive(self):
        channel = Mock()
        BufferedChannel(channel).close()
        channel.close.assert_not_called()

    def test_traversal_and_absolute_targets_blocked(self):
        for target in ['/media/%2e%2e/customer/account/', 'http://outside/a.html',
                       '//outside/a.html', '/static/../checkout/cart/add', '/media/%5cfoo']:
            self.assertFalse(allowed('GET', target))


if __name__ == '__main__':
    unittest.main()
