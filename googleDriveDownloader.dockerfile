FROM python:3.11

WORKDIR /app

COPY main.py /app
COPY poetry.lock /app
COPY pyproject.toml /app
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$PATH:$POETRY_HOME/bin"

RUN poetry install

CMD python3 main.py