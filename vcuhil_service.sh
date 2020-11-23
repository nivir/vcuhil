#!/bin/bash

export PATH="/home/vcuhil/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
exec pipenv run python3 vcuhil_service.py --log_filename /luminar/vcuhil/log/vcuhil.json
