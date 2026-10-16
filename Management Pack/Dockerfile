# The base-adapter image is bundled with the Integration SDK (1.3+) and built locally by mp-build.
FROM base-adapter:python-1.2.0
COPY commands.cfg .
COPY adapter_requirements.txt .
RUN pip3 install -r adapter_requirements.txt --upgrade
COPY app app
