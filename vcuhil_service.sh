#!/bin/bash

export PATH="/home/vcuhil/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
eval "$(pipenv run python3 vcuhil_service.py)"
