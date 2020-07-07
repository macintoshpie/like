#! /bin/bash

export FLASK_APP=like $(cat .env | xargs) && flask run
