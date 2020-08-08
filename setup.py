import re, setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('./lnregtest/__init__.py', 'r') as f:
    MATCH_EXPR = "__version__[^'\"]+(['\"])([^'\"]+)"
    VERSION = re.search(MATCH_EXPR, f.read()).group(2)

# to package, run:
# pip install setuptools wheel sdist twine
# python3 setup.py sdist bdist_wheel
setuptools.setup(
    name="lnregtest",
    version=VERSION,
    author="bitromortac",
    author_email="bitromortac@protonmail.com",
    description="Bitcoin regtest Lightning Network for integration testing.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bitromortac/lnregtest",
    packages=setuptools.find_packages(),
    install_requires=['wheel'],
    setup_requires=['wheel'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "lnregtest = lnregtest.lnregtest:main",
        ]
    },
)
