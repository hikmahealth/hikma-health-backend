<p align="centr">
<img src="https://images.squarespace-cdn.com/content/5cc0e57236f8e70001651ea6/1599789508819-NGZXYWJDQRCULLU94QEJ/hikma-hb.png?format=300w&content-type=image/png" alt="Hikma Health" />
</p>

# Hikma Health Admin Application

The Hikma Health platform is a mobile electronic health record system designed for organizations working in
low-resource settings to collect and access patient health information. The repository contains the backend
code that communicates with the Databae and ensures only authenticated users have access. Additional functionality
can be added, along with updating the correct migration files.

The platform is designed to be intuitive and allow for efficient patient workflows for patient registration, data entry, and data download. You can see a user demo here: https://drive.google.com/file/d/1ssBdEPShWCu3ZXNCXnoodbwWgqlTncJb/view?usp=drive_link

For more comprehensive documentation visit: https://docs.hikmahealth.org/

> [!IMPORTANT]
> This `main` branch has now become the default branch - migrating away from the `master` branch. This branch
> is a complete re-write of the old branch to include core dependency upgrades, api structure updates, and a
> refactor to reduce technical debt and improve organization. Migrating to this branch should be easy and
> painless - file an issue if this is not the case.
>
> If you have a local clone, you can update it by running the following commands.
>
> git branch -m next main
>
> git fetch origin
>
> git branch -u origin/main main
>
> git remote set-head origin -a

_If you are stuck for more thatn 10 minutes, please file an issue and our team can help you figure
it out 🚀. No issue is too small._

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

### Deploy the project quicly by clicking on one of these services:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/hikmahealth/hikma-health-backend/tree/master)

## Get started locally

Clone the project

```bash
  git clone git@github.com:hikmahealth/hikma-health-backend.git
```

Go to the project directory

```bash
  cd hikma-health-backend
```

Create a new virtual environment to avoid conflicts and global polution of your system

```bash
  # you can change the virtual environment folder from venv to anything you like
  python3 -m venv ./venv
```

Activate your virtual environment

```bash
  source ./venv/bin/activate

  # if windows use the following:
  # <venv>\Scripts\activate.bat
```

Install the requirements from the the `requirements.txt` file

```bash
  pip3 install -r requirements.txt
```

Start the server

```bash
  # This creates the migrations
  ./scripts/run_migrations.sh

  # This starts the service
  ./scripts/run.sh

  # IF there are no errors, you can visit: http://localhost:8000/ to see "Welcome to the Hikma Health backend."
```

Your service will start on the port specified or port 8000 by default.

To connect to a database, there are 2 options:

Option 1: Easy, Simple and Recommended Method

- Spin up a free managed database on a service like render.com (recommended)
- (optional) Download the latest version of PGAdmin, and add your DB credentials to it. This gives
  you a nice interface to manage your data directly.
- Create a new file: `.env`. in this file add a DATABASE_URL key and value.
  You get this from render.com. Look at the `.env.example` file for examples.
  **MAKE SURE YOU NEVER COMMIT YOUR PERSONAL `.env` file**

Option 2: Interesting (and possibly treacherous) Method

- Install PostgreSQL on your local computer
- Set up users with appropriate permissions
- Create a new file: `.env` (or `.env.local`). in this file add a DATABASE_URL key and value.
  You get this from render.com. Look at the `.env.example` file for examples.
  **MAKE SURE YOU NEVER COMMIT YOUR PERSONAL `.env` file**

This option is better if you wish to do most of your deployment offline,
or are running earlier version of this project. For everyone else, Option 1
is highly recommended.

_Option 2 is interesting and potentially challenging because a few things
can go wrong during the installation of PostgreSQL due to your local
computer set up, and connecting from a physical device to your server can
have its own additional steps._

_For anyone in a hurry to get things to work so that they can
focus on customizations needed for the deployment, use Option 1. As a bonus,
it gets you more comfortable with the service that will host your main deployments_

🔥 DO NOT USE THE PRODUCTION DATABASE FOR TESTING (UNLESS YOU ARE VERY CAREFUL
AND AWARE OF THE POTENTIAL CONSEQUENCES)🔥

## Environment Variables

To run this project, you will need to add the following environment
variable to your .env file

`DATABASE_URL`

This variable holds a link to the backend (server) which connects to the database.This file is by default already ignored in the `.gitignore` file, make sure it remains there.

🔥 DO NOT COMMIT THIS INFORMATION TO YOUR VERSION CONTROL (GITHUB) OR SHARE IT WITH UNAUTHORIZED PERSONEL 🔥

## Technology Stack

- **Python (v3.12):** https://docs.python.org/3/whatsnew/3.12.html
- **Flask (v3.0.2):** https://flask.palletsprojects.com/en/3.0.x/
- **SQLAlchemy (v2.0.27):** https://www.sqlalchemy.org/
- **Bcrypt (v4.1.2):** https://pypi.org/project/bcrypt/
- **Gunicorn (v21.2.0):** https://gunicorn.org/
- **PyScopePG3 (v3.2.1):** https://www.psycopg.org/psycopg3/
- **Alembic (v1.13.1):** https://pypi.org/project/alembic/

**NOTE:** If you are using python 3.11, please comment out the typing @override operator inside the `hikmahealth/entity.py` file. Please use python 3.12 to meet the requirements of this repository.

## Extras

To create a migration (after activating your virtual environment):

```bash
alembic revision -m "[Insert your change sentence summary here]"
```

To run tests using pytest, while also generating a coverage report:

```bash
python3 -m pytest --cov=hikmahealth --cov-report=term-missing --cov-report=html
```

## Roadmap

Features on the roadmap represent the vision for the admin portal over the coming versions, but none are guaranteed. If there is a feature you would love to see supported, open a feature-request / issue with more details and we can prioritize features with the most requests.

- [ ] Improve backup functionality for self-hosted options (not recommended - use a managed database service)
- [x] Add support for storing files and images
  - [x] GCP
  - [x] S3 / S3-Compatible Storage (i.e. AWS S3, Tigrisdata, Cloudflare R2)
  - [ ] Local (FS for self-hosted option) _Ideal for testing, Not Recommended_
- [x] Remove all transition code from previous deployment (all old code now lives in `oldhikma` folder for reference. This will be deleted soon.)
- [x] Add documentation for fully hosted solutions like render.com
- [x] Improve test coverage
  - [ ] 80% test coverage
- [x] Add docs to deploy button customization
- [ ] Add docs on configuring custom `server_variables`
- [ ] Add docs on configuring blob storage options. Supporting

## Contributing

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information.

## License

[MIT](https://choosealicense.com/licenses/mit/)
