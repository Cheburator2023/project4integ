# Semantic Versioning Changelog

## [1.1.15](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.14...v1.1.15) (2023-11-27)


### Bug Fixes

* **redis:** add username for redis ([618de7c](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/618de7c8e02e82c34663dfa8be6a02dc58276795))

## [1.1.14](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.13...v1.1.14) (2023-11-10)


### Bug Fixes

* **helm:** fix secret envs for fluentd definition ([5a493d1](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/5a493d1c46c83630dec58d093f37500dd79ba55e))

## [1.1.13](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.12...v1.1.13) (2023-11-10)


### Bug Fixes

* **dockerfile:** update ca certs ([42f458c](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/42f458c2a5dfa8e3086622d21b8bd1d3beb5a547))
* **helm:** update ingress version and move elk auth to secret ([d4a7fea](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/d4a7feae0ca2ef0ad39e6568ae6ba925bfe2dabd))

## [1.1.12](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.11...v1.1.12) (2023-11-08)


### Bug Fixes

* **dockerfile:** update ca certs ([46f20e0](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/46f20e01a7ae36d5b66a5d1d4d790d4bcdd2890b))

## [1.1.11](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.10...v1.1.11) (2023-08-15)


### Bug Fixes

* **kafka:** add log info on sumIgnore flag ([8ecd071](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/8ecd0719907bdabf24d833d14353dbc4fd4471a3))

## [1.1.10](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.9...v1.1.10) (2023-08-11)


### Bug Fixes

* **kafka:** delete existsEvent, add sumignore ([3583f6e](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/3583f6eef5c0a2b791bdb0debb97ce61e8155a61))
* **kafka:** return in validation all variables ([e6f7e9f](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/e6f7e9f18dfdbee6c52d72e7ecf61bc1d754db60))
* **kafka:** set camelCase for sumIgnore key ([94166e7](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/94166e700e2f52903277b485493143432b8e634a))
* **kafka:** simplify validation, not send if exsistsEvent ([814d742](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/814d74222107defe471075f7bd8b0c088aa8d59c))

## [1.1.9](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.8...v1.1.9) (2023-07-04)


### Bug Fixes

* **kafka:** add retries for kafka send method ([88a6df1](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/88a6df1872cb01f31c8e9b445c25995a86fadb9c))

## [1.1.8](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.7...v1.1.8) (2023-04-06)


### Bug Fixes

* **redis:** edit redis host url ([0c66c1c](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/0c66c1ca5f79b034b9e293e0b56d4c63600f70e6))
* **s3:** add doc for clean_versions ([777f7b6](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/777f7b6262ee7d97e2999e580f649d188a3f3896))
* **s3:** check if repo exists ([4b08793](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/4b0879323168abbff7fa58f60b0a89ee5a4639bf))
* **s3:** edit error message ([7b31ae2](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/7b31ae25c635eb5ab20d4fee0cff37ded62a32a8))
* **s3:** expand periods for store versions ([3ce3bb2](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/3ce3bb2a29b289efde0e5dbf0d2c8d40981c2c1f))
* **s3:** sync with develop ([60c8f5a](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/60c8f5ae6f9f5a17c9ec069706ed949293104696))
* **s3:** проверка для очистки версий ([1a4ac60](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/1a4ac60f9f6d18e190e68c778432af9e6b6e4cdb))

## [1.1.7](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.6...v1.1.7) (2023-02-09)


### Bug Fixes

* edit config ([3491888](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/349188822823db5d8904d9bb13685e74d749b988))
* edit configs ([7bbb436](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/7bbb43697e1c9397038ecdcf3d879c0541fd38b4))

## [1.1.6](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.5...v1.1.6) (2023-01-16)


### Bug Fixes

* **s3:** fix merge conflict ([2e4c722](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/2e4c722ce0202b364fb8cad86d7eed56a2f5126c))
* add body-max-line-length ([c2468ec](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/c2468ecfeeab6cffd18cd450f56f80cbb7ab8455))
* remove file before save for hcp ([47c42a1](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/47c42a1e110213607a9bd0ba45dc415e068bacb1))

## [1.1.5](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.4...v1.1.5) (2022-12-27)


### Bug Fixes

* add body-max-line-length ([00350f4](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/00350f405b338d752d39adc4d462fe4172788705))
* add body-max-line-length ([937451e](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/937451e352af4c51cb88028225f6ca50d796ccf0))
* add immutable true ([d4a7184](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/d4a7184bd3385895f2e70e7b11313c1a4d518113))
* change im on configmap ([dd8e6de](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/dd8e6dedde18d596622d3a54fd95ad698ed02f1c))
* edit configs ([2085bc0](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/2085bc01a446ad55d9f79cf9286c8b443f494296))
* edit configs1 ([eb8237d](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/eb8237d72cd714da9d9a1f3244241ef86bcdb7ca))

## [1.1.4](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.3...v1.1.4) (2022-10-21)

## [1.1.3](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.2...v1.1.3) (2022-10-20)

## [1.1.2](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.1...v1.1.2) (2022-10-18)

## [1.1.1](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.1.0...v1.1.1) (2022-10-17)

# [1.1.0](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.0.2...v1.1.0) (2022-10-13)


### Bug Fixes

* add elk logs ([47704aa](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/47704aaae1f52a1dcdb6a768a370a2ede5ed4448))
* **namespaces:** additional prod and test namespaces ([3766363](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/37663634a7ea626353f7b3e10aa41deb9e323dc4))
* **s3:** add error handlers for s3 ([4533e40](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/4533e405a2af5c8db2576f7baed1df6f61f31a90))
* **s3:** deny edit or update repo and proj ([1babc24](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/1babc24637d1a1ba943b82dd609b05b3e53d5eb3))
* **teamcity:** fix import json and using it ([977ecfe](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/977ecfe8dc8eb7f3466cf9bdeb230476acea6632))
* volume bug ([b0f6881](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/b0f688121acf3307780edd7232ddf00c286dac4a))
* **teamcity:** fix import json and using it ([59b0db5](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/59b0db51e3d9add6d608b3ffcefbfc6ec1fb20e8))


### Features

* replaced teamcity by k8s for running job ([407eb93](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/407eb9323422a69d343def44b6e4ef19f3387c73))

## [1.0.2](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.0.1...v1.0.2) (2022-05-12)


### Bug Fixes

* **teamcity:** validation status hotfix ([f5c45e1](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/f5c45e1b973318a34bf28eeb3b93d7bb65a3639b))
* **teamcity:** validation status hotfix ([9d5c2e0](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/9d5c2e056782d305cbf52f2b75052b43e7beeadd))

## [1.0.1](https://bitbucket.region.vtb.ru/scm/sumd/integration/compare/v1.0.0...v1.0.1) (2022-05-12)


### Bug Fixes

* add readines probe ([c881a31](https://bitbucket.region.vtb.ru/scm/sumd/integration/commit/c881a31983d81c3a947e04055d5e0bcf18a613ee))
