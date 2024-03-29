# Dinghy-ping CHANGELOG

This file is used to list changes made in each version of the Dinghy-ping 

## unreleased

## v1.3.0 (2022-07-01)
- [Zane]
  - Redesign code to match Flask best practices
    * use config.py for application configs
    * create_app function to initialize flask app from configs
    * route.py for routes, moved dinghy-ping functions to utils
    * websocket endpoints to ws.py
  - improve some error handling

## v1.2.1 (2022-06-24)
- [Zane]
  - black, isort, flake8 fixes
  - fixing event log stream logging wording, remove asyncio reference
 
## v1.2.0 (2022-06-24)
- [Zane]
  - Use wtform validations
  - remove url access to dns, http and tcp checks (must go through form input)
  - fix: socket timeouts now work
  - fix: remove async tcp checks
  - add dns checks to search history results
  - remove schema check in code, URLField will not enforce in wtform inputs

## v1.1.1 (2022-03-29)
- [Zane] 
  - Cleanup boot.sh and Dockerfile INFO gunicorn log level 

## v1.1.0 (2022-03-29)
- [Zane] 
  - Adding support for multiple containers in pods

## v1.0.0 (2022-03-29)
- [Zane]
  - rebuild application using Flask, dropping Responder framework

## v0.5.2 (2022-03-24)
- [Zane]
  - fixing websocket support to work with Tilt localhost development 

## v0.5.1 (2022-03-24)
- [Zane]
  - pyyaml version bump fix security issue

## v0.5.0 (2022-03-24)
- [Zane] 
  - Redis stateful set for search results
  - New helm chart
  - New github action workflows

## v0.4.3 (2020-01-28)
- [Zane] - Tail log option, keep static log output

## v0.4.2 (2020-01-28)
- [Zane] - Scroll down and append logs 

## v0.4.1 (2020-01-21)
- [Zane] - Use wss for secure requests

## v0.4.0 (2020-01-19)
- [Zane] - Adding websocket stream logs support, PEP8 fixes

## v0.3.5 (2019-11-25)
- [Zane] - Fixing list layout for pods by namespace 

## v0.3.4 (2019-11-25)
- [Zane] - New pod look up page, no user input required

## v0.3.3 (2019-11-15)
- [Tatiana] - Refactor code layout
- [Zane] - Fix static image location
- [Zane] - Adding describe pod

## v0.3.2 (2019-07-26)
- [Zane] - Remove overflow hidden in CSS. This is causing multiple line log entries from being shown 

## v0.3.1 (2019-07-26)
- [Zane] - adding max-h-full to fix truncated logout in HTML

## v0.3.0 (2019-07-26)

- [Zane]
  * Tail lines feature, default 100. This changes behavior of log viewing
  * Add parameter option for preview line numbers
  * Update function docs

## v0.2.0 (2019-07-24)

- [Zane, Ian, Tatiana, Bassam, Kristin] - New UI, pod logs, deployment logs

## v0.1.2 (2019-06-26)

- [Zane] - Use default system resolver, and optional nameserver override

## v0.1.1 (2019-06-25)

- [Zane] - Adding DNS lookup interface
- [Sandosh] - Display response headers and syntax highlight response

## v0.1.0 (2019-05-22)

- [Zane Williamson] - Upgrade to Tailwind CSS v1.0 and lock in version

## v0.0.17 (2019-05-01)

- [Zane Williamson] - Moving history to upper right, adding slivermullet logo 

## v0.0.16 (2019-05-01)

- [Zane Williamson] - Security and dependency updates 

## v0.0.15 (2019-01-26)

- [Zane Williamson] - Save tcp tests to history, Travis test with Python 3.7 

## v0.0.14 (2019-01-14)

- [Zane Williamson] - Adding TCP check feature

## v0.0.13 (2019-01-13)

- [Zane Williamson] - Fix https://github.com/silvermullet/dinghy-ping/issues/39, better error handling, deliever results even if redis not available 

## v0.0.12 (2019-01-10)

- [Zane Williamson] - Adding header input support, using Tailwind CSS for form

## v0.0.11 (2018-12-29)

- [Zane Williamson]
  * Exposing Prometheus metrics
  * Fix starlette dependency version issue (see here)[https://github.com/kennethreitz/responder/issues/266]
  * Updating local development docs

## v0.0.10 (2018-11-22)

- [Zane Williamson] - Adding response code and response time to history

## v0.0.9 (2018-11-22)

- [Zane Williamson] - Add redis support for storing and retrieving ping results, present history on input page
- [Ian Morgan] - Adding redis side car with pvc to Helm chart 

## v0.0.8 (2018-11-19)

- [Zane Williamson] - Add link back to search form 
- [Ian Morgan] - Fix timeout issue in Issue [28](https://github.com/silvermullet/dinghy-ping/issues/28)

## v0.0.7 (2018-11-13)

- [Zane Williamson] - Spruce up ping response template, using Tailwind CSS

## v0.0.6 (2018-11-13)

- [Zane Williamson]
 * Include full request in ping results page
 * Set default scheme to https if none requested - fix issue [25](https://github.com/silvermullet/dinghy-ping/issues/25)

## v0.0.5 (2018-11-01)

- [Ian Morgan] - Form input on landing page. HAWT 

## v0.0.4 (2018-10-29)

- [Zane Williamson] - Better error handling on request process 

## v0.0.3 (2018-10-28)

- [Zane Williamson] - Refactor multiple domain response, adding intial pytests 

## v0.0.2 (2018-10-22)

- [Zane Williamson] - Adding multiple domain support, travis build process for docker 
