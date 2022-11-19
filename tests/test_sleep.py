from unittest.mock import MagicMock, patch

import pytest
import weechat

from slack.task import FutureTimer, sleep, weechat_task_cb


@patch.object(weechat, "hook_timer")
def test_sleep(mock_method: MagicMock):
    milliseconds = 123
    coroutine = sleep(milliseconds)
    future = coroutine.send(None)
    assert isinstance(future, FutureTimer)

    mock_method.assert_called_once_with(
        milliseconds, 0, 1, weechat_task_cb.__name__, future.id
    )

    with pytest.raises(StopIteration) as excinfo:
        coroutine.send((0,))
    assert excinfo.value.value == (0,)  # TODO: Will probably change to None