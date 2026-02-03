# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Ramkumar78/OptionThetaRisk/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| option\_auditor/backtesting\_strategies.py          |      393 |       79 |     80% |16, 21, 26, 31, 41, 197, 223, 235-237, 240-242, 245, 248-251, 256-258, 261-263, 266, 269-272, 307-309, 312-315, 318, 321-324, 329-331, 334-336, 339, 342-345, 350-352, 355-356, 359, 362-365, 390, 401, 421-422, 435-436, 471-476, 501, 503, 507, 509, 511, 520 |
| option\_auditor/cli.py                              |       57 |        4 |     93% |71-73, 101 |
| option\_auditor/common/constants.py                 |       23 |        2 |     91% |   444-445 |
| option\_auditor/common/data\_utils.py               |      184 |       37 |     80% |25-26, 49-52, 78-82, 89-90, 94-98, 102-103, 107-108, 119-120, 158, 189, 204-206, 218, 221-222, 239-240, 249-250, 302-303 |
| option\_auditor/common/file\_utils.py               |       28 |       11 |     61% |15-16, 21-28, 36, 49-51 |
| option\_auditor/common/resilience.py                |       10 |        0 |    100% |           |
| option\_auditor/common/screener\_utils.py           |      270 |       73 |     73% |23-24, 44, 53-55, 64-98, 110-112, 114, 120, 161-170, 195-198, 200-203, 217-220, 222-224, 226-228, 253-254, 260-262, 348-349, 378, 425-431 |
| option\_auditor/common/signal\_type.py              |        6 |        0 |    100% |           |
| option\_auditor/config.py                           |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py               |       16 |        2 |     88% |     19-20 |
| option\_auditor/journal\_analyzer.py                |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py                   |      570 |       61 |     89% |97-98, 120, 166, 193, 198, 245, 249-255, 271-272, 277-279, 359, 413, 436, 444-445, 461-465, 486, 496-497, 501-502, 518, 524-525, 556-557, 573, 598-599, 607-616, 647, 680-683, 761-762, 766-768, 780-781, 865, 935 |
| option\_auditor/models.py                           |       75 |        2 |     97% |    76, 91 |
| option\_auditor/monte\_carlo\_simulator.py          |       39 |        1 |     97% |        19 |
| option\_auditor/parsers.py                          |      272 |       63 |     77% |15, 24-26, 30-44, 132-133, 160, 162-163, 180-214, 321-323, 335-336, 345, 378 |
| option\_auditor/portfolio\_risk.py                  |      190 |       35 |     82% |68-71, 81-83, 87, 94, 123-131, 186, 202, 234, 259-264, 269, 271, 288, 299-302, 319, 336-338, 380-382 |
| option\_auditor/risk\_intelligence.py               |       44 |        4 |     91% |     50-57 |
| option\_auditor/screener.py                         |       54 |        3 |     94% |   138-140 |
| option\_auditor/sp500\_data.py                      |       34 |        5 |     85% |31-32, 50-53 |
| option\_auditor/strategies/\_\_init\_\_.py          |        6 |        0 |    100% |           |
| option\_auditor/strategies/alpha.py                 |      102 |       21 |     79% |45-46, 51-52, 90-91, 151-163, 169, 198-199 |
| option\_auditor/strategies/base.py                  |       19 |        4 |     79% |15, 23, 32-33 |
| option\_auditor/strategies/bull\_put.py             |      114 |        9 |     92% |53, 95-96, 131, 140, 222-224, 234-235 |
| option\_auditor/strategies/darvas.py                |       90 |       13 |     86% |42, 103, 106-107, 119-123, 126, 160-162 |
| option\_auditor/strategies/five\_thirteen.py        |       98 |       13 |     87% |79-80, 112-113, 128-131, 144, 179-182 |
| option\_auditor/strategies/fortress.py              |       78 |       19 |     76% |16-18, 31, 45-48, 53, 59-60, 81-82, 94-95, 100-101, 135-137 |
| option\_auditor/strategies/fourier.py               |       57 |        2 |     96% |   112-113 |
| option\_auditor/strategies/grandmaster\_screener.py |       64 |        7 |     89% |52-58, 117 |
| option\_auditor/strategies/hybrid.py                |      279 |       64 |     77% |29-30, 37-38, 49-52, 55-76, 146-147, 164-166, 182-184, 230, 263, 278, 289-291, 302-307, 313, 315, 317, 319, 325-328, 333, 336-337, 347, 355-357, 374-375, 393-394, 426-428 |
| option\_auditor/strategies/isa.py                   |      100 |        9 |     91% |61, 73-77, 142, 147, 186-188 |
| option\_auditor/strategies/liquidity.py             |       90 |        6 |     93% |38, 75-77, 174-175 |
| option\_auditor/strategies/market.py                |      182 |       40 |     78% |38-39, 59, 61, 65-68, 85, 122-123, 153-154, 167-168, 173, 201-203, 241-247, 250, 258, 297-327 |
| option\_auditor/strategies/master.py                |      150 |       41 |     73% |35, 40-45, 48, 58, 64-66, 101-102, 111, 121-123, 125-127, 162-166, 168, 185-201, 213, 240-242 |
| option\_auditor/strategies/math\_utils.py           |      183 |       19 |     90% |59-60, 84-85, 111, 132-133, 154, 160-161, 190-191, 201-202, 231-232, 306, 361-362 |
| option\_auditor/strategies/mms\_ote.py              |       86 |        6 |     93% |119-120, 143-146 |
| option\_auditor/strategies/monte\_carlo.py          |       29 |        6 |     79% |23-25, 60-62 |
| option\_auditor/strategies/options\_only.py         |      144 |       23 |     84% |47-48, 92-95, 103-106, 111-112, 127-128, 148, 154-155, 196, 207, 230-232, 244-245 |
| option\_auditor/strategies/quantum.py               |       69 |       10 |     86% |27, 58-59, 92-93, 101-102, 126-128 |
| option\_auditor/strategies/rsi\_divergence.py       |       75 |        3 |     96% |99, 126-127 |
| option\_auditor/strategies/squeeze.py               |       40 |        2 |     95% |     86-87 |
| option\_auditor/strategies/turtle.py                |       76 |        6 |     92% |58-59, 62, 137-139 |
| option\_auditor/strategies/utils.py                 |        1 |        0 |    100% |           |
| option\_auditor/strategies/vertical\_spreads.py     |      140 |       28 |     80% |26, 32-37, 40-41, 47-48, 60, 70, 86-87, 119-124, 133-135, 158-159, 179, 192, 259-261 |
| option\_auditor/strategy.py                         |      256 |       33 |     87% |16, 35, 148-155, 204, 207-245, 279, 306 |
| option\_auditor/uk\_stock\_data.py                  |       16 |        2 |     88% |     30-31 |
| option\_auditor/unified\_backtester.py              |      190 |        7 |     96% |37-39, 46, 74, 106, 341, 358 |
| option\_auditor/unified\_screener.py                |      125 |       29 |     77% |37, 41-42, 48, 59-63, 78-81, 96-97, 120-123, 178-180, 191-197, 203, 220-223, 238-239 |
| option\_auditor/us\_stock\_data.py                  |        9 |        3 |     67% |     50-53 |
| webapp/\_\_init\_\_.py                              |        0 |        0 |    100% |           |
| webapp/app.py                                       |       75 |       14 |     81% |37-38, 73-76, 99-100, 104-105, 120-126 |
| webapp/blueprints/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| webapp/blueprints/analysis\_routes.py               |      158 |       47 |     70% |24-36, 40-52, 61, 72-74, 88, 95, 99-101, 120-122, 129-130, 144, 152-160, 209-211 |
| webapp/blueprints/journal\_routes.py                |       79 |       17 |     78% |27, 37-39, 62, 71-79, 104-106 |
| webapp/blueprints/main\_routes.py                   |       60 |        9 |     85% |36-38, 46, 60-62, 76, 81 |
| webapp/blueprints/screener\_routes.py               |      487 |       64 |     87% |57-58, 63-64, 74-75, 125-126, 133-134, 138, 179, 228-229, 249-252, 257-258, 264, 270-275, 282-283, 289, 296-299, 311, 317-320, 339, 358, 377, 396, 415, 435, 455, 474, 494-495, 526, 540, 559, 577, 595, 638-641, 650, 656-657, 668, 674-679 |
| webapp/cache.py                                     |       28 |        1 |     96% |        34 |
| webapp/main.py                                      |       20 |        2 |     90% |     34-35 |
| webapp/services/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| webapp/services/check\_service.py                   |       77 |       16 |     79% |54, 64, 72, 77-80, 87-94, 99-102 |
| webapp/services/scheduler\_service.py               |       38 |       12 |     68% |37-39, 45-46, 52-58 |
| webapp/storage.py                                   |      393 |       30 |     92% |68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 117, 270, 347-348, 388, 423-424, 443-446, 463, 480-481, 492, 504-505, 524 |
| webapp/utils.py                                     |       50 |        7 |     86% |32-33, 58-59, 69-71 |
| **TOTAL**                                           | **6668** | **1029** | **85%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/Ramkumar78/OptionThetaRisk/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/Ramkumar78/OptionThetaRisk/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Ramkumar78/OptionThetaRisk/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/Ramkumar78/OptionThetaRisk/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FRamkumar78%2FOptionThetaRisk%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/Ramkumar78/OptionThetaRisk/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.