"""Run mp-build where there is no Windows console (Git Bash, CI, Claude Code).

The Integration SDK prints through prompt_toolkit, which needs a real console on
Windows and otherwise crashes partway through the build. This gives it plain-text
output instead. Arguments are passed to mp-build unchanged.
"""
import sys

from prompt_toolkit.application.current import create_app_session
from prompt_toolkit.output.plain_text import PlainTextOutput
from vmware_aria_operations_integration_sdk.mp_build import main

sys.argv = ["mp-build"] + sys.argv[1:]
with create_app_session(output=PlainTextOutput(sys.stdout)):
    main()
