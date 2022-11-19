import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from slack.init import main  # pylint: disable=wrong-import-position
from slack.shared import shared  # pylint: disable=wrong-import-position

shared.weechat_callbacks = globals()

if __name__ == "__main__":
    main()