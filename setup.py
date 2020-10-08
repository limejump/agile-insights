import setuptools

setuptools.setup(
    name="scrum-dashboard",
    version="0.0.1",
    auther="Grahame Gardiner",
    author_email="grahame.gardiner@limejump.com",
    description=(
        "An ETL for fetching scrum board data pertinent to forecasting "
        "And a dashboard for presenting it."
        ),
    packages=setuptools.find_packages(),
    install_requires=[
        'arrow',
        'click',
        'dash',
        'dash-bootstrap-components',
        'pandas',
        'pymongo',
        'requests'
    ],
    extras_require={
        'test': [
            'pytest',
            'lenses'
        ],
        'migrate': [
            'pymongo-migrate'
        ]
    }
)
