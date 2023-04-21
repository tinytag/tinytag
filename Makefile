LATEST := $(shell bash -c "find dist | sort -V -r | head -n 1")

.PHONY : all
all: upload

test:
	pytest

assure_tag_is_version:
	bash -c 'grep `git tag | sort -V | tail -1` tinytag/__init__.py'  || (echo "git version is not the same as version in __init__.py"; exit 1)

buildpkg: assure_tag_is_version test
	python ./setup.py sdist

upload: buildpkg
	bash -c 'twine upload -r pypi `find dist | sort -V -r | head -n 1`'

