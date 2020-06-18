# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Test widgets in miscwidgets module."""

import logging
from unittest import mock

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QApplication, QWidget
import pytest

from qutebrowser.misc import miscwidgets
from qutebrowser.browser import inspector


class TestCommandLineEdit:

    """Tests for CommandLineEdit widget."""

    @pytest.fixture
    def cmd_edit(self, qtbot):
        """Fixture to initialize a CommandLineEdit."""
        cmd_edit = miscwidgets.CommandLineEdit()
        cmd_edit.set_prompt(':')
        qtbot.add_widget(cmd_edit)
        assert cmd_edit.text() == ''
        yield cmd_edit

    @pytest.fixture
    def mock_clipboard(self, mocker):
        """Fixture to mock QApplication.clipboard.

        Return:
            The mocked QClipboard object.
        """
        mocker.patch.object(QApplication, 'clipboard')
        clipboard = mock.MagicMock()
        clipboard.supportsSelection.return_value = True
        QApplication.clipboard.return_value = clipboard
        return clipboard

    def test_position(self, qtbot, cmd_edit):
        """Test cursor position based on the prompt."""
        qtbot.keyClicks(cmd_edit, ':hello')
        assert cmd_edit.text() == ':hello'
        assert cmd_edit.cursorPosition() == len(':hello')

        cmd_edit.home(True)
        assert cmd_edit.cursorPosition() == len(':')
        qtbot.keyClick(cmd_edit, Qt.Key_Delete)
        assert cmd_edit.text() == ':'
        qtbot.keyClick(cmd_edit, Qt.Key_Backspace)
        assert cmd_edit.text() == ':'

        qtbot.keyClicks(cmd_edit, 'hey again')
        assert cmd_edit.text() == ':hey again'

    def test_invalid_prompt(self, qtbot, cmd_edit):
        """Test preventing of an invalid prompt being entered."""
        qtbot.keyClicks(cmd_edit, '$hello')
        assert cmd_edit.text() == ''

    def test_selection_home(self, qtbot, cmd_edit):
        """Test selection persisting when pressing home."""
        qtbot.keyClicks(cmd_edit, ':hello')
        assert cmd_edit.text() == ':hello'
        assert cmd_edit.cursorPosition() == len(':hello')
        cmd_edit.home(True)
        assert cmd_edit.cursorPosition() == len(':')
        assert cmd_edit.selectionStart() == len(':')

    def test_selection_cursor_left(self, qtbot, cmd_edit):
        """Test selection persisting when moving to the first char."""
        qtbot.keyClicks(cmd_edit, ':hello')
        assert cmd_edit.text() == ':hello'
        assert cmd_edit.cursorPosition() == len(':hello')
        for _ in ':hello':
            qtbot.keyClick(cmd_edit, Qt.Key_Left, modifier=Qt.ShiftModifier)
        assert cmd_edit.cursorPosition() == len(':')
        assert cmd_edit.selectionStart() == len(':')


class WrappedWidget(QWidget):

    def sizeHint(self):
        return QSize(23, 42)


class TestWrapperLayout:

    @pytest.fixture
    def container(self, qtbot):
        wrapped = WrappedWidget()
        parent = QWidget()
        qtbot.add_widget(wrapped)
        qtbot.add_widget(parent)
        layout = miscwidgets.WrapperLayout(parent)
        layout.wrap(parent, wrapped)
        parent.wrapped = wrapped
        return parent

    def test_size_hint(self, container):
        assert container.sizeHint() == QSize(23, 42)

    def test_wrapped(self, container):
        assert container.wrapped.parent() is container
        assert container.focusProxy() is container.wrapped


class TestFullscreenNotification:

    @pytest.mark.parametrize('bindings, text', [
        ({'<escape>': 'fullscreen --leave'},
         "Press <Escape> to exit fullscreen."),
        ({'<escape>': 'fullscreen'}, "Page is now fullscreen."),
        ({'a': 'fullscreen --leave'}, "Press a to exit fullscreen."),
        ({}, "Page is now fullscreen."),
    ])
    def test_text(self, qtbot, config_stub, key_config_stub, bindings, text):
        config_stub.val.bindings.default = {}
        config_stub.val.bindings.commands = {'normal': bindings}
        w = miscwidgets.FullscreenNotification()
        qtbot.add_widget(w)
        assert w.text() == text

    def test_timeout(self, qtbot, key_config_stub):
        w = miscwidgets.FullscreenNotification()
        qtbot.add_widget(w)
        with qtbot.waitSignal(w.destroyed):
            w.set_timeout(1)


class TestInspectorSplitter:

    @pytest.fixture
    def fake_webview(self, qtbot):
        webview = QWidget()
        webview.setStyleSheet('background-color: blue;')
        qtbot.add_widget(webview)
        return webview

    @pytest.fixture
    def fake_inspector(self, qtbot):
        inspector = QWidget()
        inspector.setStyleSheet('background-color: red;')
        qtbot.add_widget(inspector)
        return inspector

    @pytest.fixture
    def splitter(self, qtbot, fake_webview):
        inspector_splitter = miscwidgets.InspectorSplitter(fake_webview)
        qtbot.add_widget(inspector_splitter)
        return inspector_splitter

    @pytest.fixture(autouse=True)
    def state_config(self, monkeypatch):
        state = {'geometry': {}}
        monkeypatch.setattr(miscwidgets.configfiles, 'state', state)
        return state

    def test_no_inspector(self, splitter, fake_webview):
        assert splitter.count() == 1
        assert splitter.widget(0) is fake_webview
        assert splitter.focusProxy() is fake_webview

    def test_no_inspector_resize(self, splitter):
        splitter.show()
        splitter.resize(800, 600)

    @pytest.mark.parametrize(
        'position, orientation, inspector_idx, webview_idx', [
            (inspector.Position.left, Qt.Horizontal, 0, 1),
            (inspector.Position.right, Qt.Horizontal, 1, 0),
            (inspector.Position.top, Qt.Vertical, 0, 1),
            (inspector.Position.bottom, Qt.Vertical, 1, 0),
        ]
    )
    def test_set_inspector(self, position, orientation,
                           inspector_idx, webview_idx,
                           splitter, fake_inspector, fake_webview):
        splitter.set_inspector(fake_inspector, position)

        assert splitter.indexOf(fake_inspector) == inspector_idx
        assert splitter._inspector_idx == inspector_idx

        assert splitter.indexOf(fake_webview) == webview_idx
        assert splitter._main_idx == webview_idx

        assert splitter.orientation() == orientation

    @pytest.mark.parametrize(
        'config, width, height, position, expected_size', [
            # No config but enough big window
            (
                {},
                1024, 768,
                inspector.Position.left,
                512,
            ),
            (
                {},
                1024, 768,
                inspector.Position.top,
                384,
            ),

            # No config and small window
            (
                {},
                320, 240,
                inspector.Position.left,
                300,
            ),
            (
                {},
                320, 240,
                inspector.Position.top,
                300,
            ),

            # Invalid config
            (
                {'inspector_left': 'verybig'},
                1024, 768,
                inspector.Position.left,
                512,
            ),

            # Different config
            (
                {'inspector_right': '666'},
                1024, 768,
                inspector.Position.left,
                512,
            ),

            # Value from config
            (
                {'inspector_left': '666'},
                1024, 768,
                inspector.Position.left,
                666,
            ),
        ]
    )
    def test_read_size(self, config, width, height, position, expected_size,
                       state_config, splitter, fake_inspector, caplog):
        state_config['geometry'] = config

        splitter.resize(width, height)
        assert splitter.size() == QSize(width, height)

        with caplog.at_level(logging.ERROR):
            splitter.set_inspector(fake_inspector, position)

        assert splitter._preferred_size == expected_size

        if config == {'inspector_left': 'verybig'}:
            assert caplog.messages == ["Could not read inspector size: "
                                       "invalid literal for int() with "
                                       "base 10: 'verybig'"]

    @pytest.mark.parametrize('position, key', [
        (inspector.Position.left, 'inspector_left'),
        (inspector.Position.right, 'inspector_right'),
        (inspector.Position.top, 'inspector_top'),
        (inspector.Position.bottom, 'inspector_bottom'),
    ])
    def test_save_size(self, position, key,
                       state_config, splitter, fake_inspector):
        splitter.set_inspector(fake_inspector, position)
        splitter._preferred_size = 1337
        splitter._save_preferred_size()
        assert state_config['geometry'][key] == '1337'

    @pytest.mark.parametrize(
        'old_window_size, preferred_size, new_window_size, '
        'exp_inspector_size', [
            # Plenty of space -> Keep inspector at configured absolute size
            (1000, 500,  # 1/2 of window
             800, 500),  # 500px -> 500px

            # Slowly running out of space -> Reserve space for website
            (1000, 750,  # 3/4 of window
             500, 350),  # 750px -> 350px (so website has 150px)

            # Very small window -> Keep ratio distribution
            (1000, 500,  # 1/2 of window
             200, 100),  # 500px -> 100px (1/2)
        ]
    )
    @pytest.mark.parametrize('position', [
        inspector.Position.left, inspector.Position.right,
        inspector.Position.top, inspector.Position.bottom])
    def test_adjust_size(self, old_window_size, preferred_size,
                         new_window_size, exp_inspector_size,
                         position, splitter, fake_inspector, qtbot):
        def resize(size):
            if splitter.orientation() == Qt.Horizontal:
                splitter.resize(size, 600)
                assert splitter.size() == QSize(size, 600)
            else:
                splitter.resize(1024, size)
                assert splitter.size() == QSize(1024, size)

        splitter.set_inspector(fake_inspector, position)
        splitter.show()
        resize(old_window_size)

        handle_width = splitter.handleWidth()
        splitter_idx = 1
        if position in [inspector.Position.left, inspector.Position.top]:
            splitter_pos = preferred_size - handle_width//2
        else:
            splitter_pos = old_window_size - preferred_size - handle_width//2
        splitter.moveSplitter(splitter_pos, splitter_idx)

        resize(new_window_size)

        sizes = splitter.sizes()
        inspector_size = sizes[splitter._inspector_idx]
        main_size = sizes[splitter._main_idx]
        exp_main_size = new_window_size - exp_inspector_size - handle_width//2
        exp_inspector_size -= handle_width//2

        assert (inspector_size, main_size) == (exp_inspector_size,
                                               exp_main_size)
