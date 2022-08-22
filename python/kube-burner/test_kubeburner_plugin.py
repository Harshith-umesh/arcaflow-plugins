#!/usr/bin/env python3

import re
import unittest
import kubeburner_plugin
from arcaflow_plugin_sdk import plugin


class SysbenchPluginTest(unittest.TestCase):
    @staticmethod
    def test_serialization():
        plugin.test_object_serialization(
            kubeburner_plugin.KubeBurnerIndexerInputParams(
                collection_time=30,
                es_server="https://search-dev-chm.west-2.es.amazonaws.com:443",
                es_index="index"
                )
        )

        plugin.test_object_serialization(
            kubeburner_plugin.WorkloadError(
                exit_code=1,
                error="This is an error"
            )
        )
      


if __name__ == '__main__':
    unittest.main()
