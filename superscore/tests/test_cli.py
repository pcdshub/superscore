"""Tests for cli endpoints"""
import sys

import pytest

import superscore.bin.demo as demo_main
import superscore.bin.main as ss_main
from superscore.tests.ioc.ioc_factory import TempIOC


def test_cli_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["superscore", "demo", "--help"])
    with pytest.raises(SystemExit):
        ss_main.main()


@pytest.mark.parametrize('subcommand', list(ss_main.MODULES))
def test_help_module(monkeypatch, subcommand: str):
    monkeypatch.setattr(sys, "argv", ["superscore", subcommand, "--help"])
    with pytest.raises(SystemExit):
        ss_main.main()


def test_demo_smoke(monkeypatch):
    """
    This primarily tests demo backend gathering, ui component creation tested
    elsewhere
    """
    def mockreturn(*args, **kwargs):
        return

    monkeypatch.setattr(sys, "argv", ["superscore", "demo"])
    # Prevent qt components from being created, since we can't fully clean up
    monkeypatch.setattr(demo_main, 'ui_main', mockreturn)
    monkeypatch.setattr(TempIOC, "__enter__", mockreturn)
    ss_main.main()
