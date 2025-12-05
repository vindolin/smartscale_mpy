#!/usr/bin/fish
mpremote fs cp fs/$argv[1] :
mpremote soft-reset
mpremote eval "run()"
