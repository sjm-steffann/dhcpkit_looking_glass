"""
Miscellaneous utilities for the looking glass
"""
import json
import re
from collections import OrderedDict

import yaml
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from typing import Optional


def json_message_to_html(json_message: Optional[str]) -> Optional[str]:
    """
    Show a message (which is stored as JSON in the database) as YAML with some highlighting.

    :param json_message: The JSON string
    :return: The HTML representation
    """
    if not json_message:
        return None

    response_yaml = yaml.dump(json.loads(json_message, object_pairs_hook=OrderedDict),
                              default_flow_style=False)
    response_html = format_html('<pre style="float: left; margin: 0">{}</pre>', response_yaml)
    response_html = re.sub(r'([a-zA-Z0-9]+Message:)', r'<b>\1</b>', response_html)
    return mark_safe(response_html)
