# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Ramkumar78/OptionThetaRisk/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| option\_auditor/analysis\_worker.py                 |       90 |       29 |     68% |27-28, 32-40, 51-53, 70-72, 76-78, 103-105, 116-118, 122, 125-127 |
| option\_auditor/backtest\_data\_loader.py           |       53 |        3 |     94% | 57-59, 66 |
| option\_auditor/backtest\_engine.py                 |      117 |        4 |     97% |29, 35, 63, 67 |
| option\_auditor/backtest\_reporter.py               |       87 |        1 |     99% |       120 |
| option\_auditor/backtesting\_strategies.py          |      402 |       82 |     80% |17, 22, 27, 32, 36, 80, 98, 243-245, 248-250, 253, 256-259, 267-269, 272-274, 277, 280-283, 306, 318-320, 323-326, 329, 332-335, 340-342, 345-347, 350, 353-356, 361-363, 366-367, 370, 373-376, 401, 412, 432-433, 446-447, 482-487, 512, 514, 518, 520, 522, 529-533 |
| option\_auditor/cli.py                              |       57 |        4 |     93% |71-73, 101 |
| option\_auditor/common/constants.py                 |       23 |        2 |     91% |   444-445 |
| option\_auditor/common/data\_utils.py               |      239 |       45 |     81% |25-26, 61-64, 90-94, 101-102, 106-110, 114-115, 119-120, 131-132, 201, 216-218, 230, 233-234, 251-252, 261-262, 411-413, 421-422, 430-437 |
| option\_auditor/common/file\_utils.py               |       28 |        0 |    100% |           |
| option\_auditor/common/price\_utils.py              |       69 |       11 |     84% |38, 43, 90, 94-100, 122-124 |
| option\_auditor/common/resilience.py                |       10 |        0 |    100% |           |
| option\_auditor/common/screener\_utils.py           |      273 |       51 |     81% |23-24, 44, 53-55, 68, 74, 84, 94-96, 110-112, 114, 120, 161-170, 196-199, 201-204, 218-221, 223-225, 227-229, 236, 257-258, 264-266, 352-353 |
| option\_auditor/common/serialization.py             |       30 |        5 |     83% |29, 43, 49-51 |
| option\_auditor/common/signal\_type.py              |        6 |        0 |    100% |           |
| option\_auditor/config.py                           |        9 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py               |       35 |        7 |     80% |21-22, 36, 41-43, 46 |
| option\_auditor/journal\_analyzer.py                |      148 |       13 |     91% |95, 133-134, 140, 181-182, 194-195, 234-235, 268-272 |
| option\_auditor/main\_analyzer.py                   |      534 |       49 |     91% |105-106, 222, 245, 253-254, 295, 305-306, 310-311, 327, 333-334, 397-400, 427-428, 444, 469-470, 478-487, 518, 555-558, 624-625, 629-631, 643-644, 665-667, 735, 807 |
| option\_auditor/models.py                           |      102 |        2 |     98% |   85, 100 |
| option\_auditor/monte\_carlo\_simulator.py          |       70 |        2 |     97% |   21, 142 |
| option\_auditor/parsers.py                          |      283 |       47 |     83% |15, 41, 132-133, 160, 162-163, 180-214, 321-323, 335-336, 345, 378 |
| option\_auditor/portfolio\_risk.py                  |      274 |       51 |     81% |68-71, 81-83, 87, 94, 123-131, 202, 234, 259-264, 269, 271, 288, 299-302, 319, 336-338, 380-382, 396, 417-420, 423, 425, 436, 444-447, 479-480, 514-516 |
| option\_auditor/risk\_analyzer.py                   |      165 |        6 |     96% |    99-104 |
| option\_auditor/risk\_engine\_pro.py                |       61 |        2 |     97% |  102, 114 |
| option\_auditor/risk\_intelligence.py               |      128 |       17 |     87% |51-58, 155-156, 171-172, 183-188, 210-211, 234-236 |
| option\_auditor/screener.py                         |       60 |        5 |     92% |140-142, 172, 188 |
| option\_auditor/sp500\_data.py                      |       34 |        5 |     85% |31-32, 50-53 |
| option\_auditor/strategies/\_\_init\_\_.py          |        6 |        0 |    100% |           |
| option\_auditor/strategies/alpha.py                 |      102 |       21 |     79% |45-46, 51-52, 90-91, 151-163, 169, 198-199 |
| option\_auditor/strategies/base.py                  |       24 |        5 |     79% |15, 21, 32, 41-42 |
| option\_auditor/strategies/bull\_put.py             |      114 |        9 |     92% |53, 95-96, 131, 140, 222-224, 234-235 |
| option\_auditor/strategies/darvas.py                |       90 |       13 |     86% |42, 103, 106-107, 119-123, 126, 160-162 |
| option\_auditor/strategies/five\_thirteen.py        |       98 |       13 |     87% |79-80, 112-113, 128-131, 144, 179-182 |
| option\_auditor/strategies/fortress.py              |       78 |       14 |     82% |16-18, 31, 53, 81-82, 94-95, 100-101, 135-137 |
| option\_auditor/strategies/fourier.py               |       57 |        2 |     96% |   112-113 |
| option\_auditor/strategies/grandmaster\_screener.py |       64 |        7 |     89% |52-58, 117 |
| option\_auditor/strategies/hybrid.py                |      279 |       64 |     77% |29-30, 37-38, 49-52, 55-76, 146-147, 164-166, 182-184, 230, 263, 278, 289-291, 302-307, 313, 315, 317, 319, 325-328, 333, 336-337, 347, 355-357, 374-375, 393-394, 426-428 |
| option\_auditor/strategies/isa.py                   |      148 |       17 |     89% |48-49, 63, 71-72, 89, 104-105, 143, 155-159, 224, 229, 278-280 |
| option\_auditor/strategies/liquidity.py             |       90 |        6 |     93% |38, 75-77, 174-175 |
| option\_auditor/strategies/market.py                |      182 |       40 |     78% |38-39, 59, 61, 65-68, 85, 122-123, 153-154, 167-168, 173, 201-203, 241-247, 250, 258, 297-327 |
| option\_auditor/strategies/master.py                |      150 |       27 |     82% |35, 40-45, 48, 64-66, 101-102, 111, 127, 162-166, 168, 178-180, 189, 213, 241-243 |
| option\_auditor/strategies/math\_utils.py           |      198 |       19 |     90% |59-60, 84-85, 111, 132-133, 160-161, 190-191, 201-202, 231-232, 361-362, 386-387 |
| option\_auditor/strategies/medallion\_isa.py        |       63 |        8 |     87% |71-74, 97, 116-118 |
| option\_auditor/strategies/mms\_ote.py              |       86 |        6 |     93% |119-120, 143-146 |
| option\_auditor/strategies/monte\_carlo.py          |       29 |        6 |     79% |23-25, 60-62 |
| option\_auditor/strategies/options\_only.py         |      144 |       23 |     84% |47-48, 92-95, 103-106, 111-112, 127-128, 148, 154-155, 196, 207, 230-232, 244-245 |
| option\_auditor/strategies/quality\_200w.py         |       70 |       21 |     70% |25, 32, 37, 45, 63, 67, 74, 106-136, 158 |
| option\_auditor/strategies/quantum.py               |       69 |       10 |     86% |27, 58-59, 92-93, 101-102, 126-128 |
| option\_auditor/strategies/rsi\_divergence.py       |       75 |        3 |     96% |99, 126-127 |
| option\_auditor/strategies/rsi\_reversal.py         |       60 |        4 |     93% |15, 22, 41, 78 |
| option\_auditor/strategies/squeeze.py               |       40 |        2 |     95% |     86-87 |
| option\_auditor/strategies/turtle.py                |       76 |        6 |     92% |58-59, 62, 137-139 |
| option\_auditor/strategies/utils.py                 |        1 |        1 |      0% |         1 |
| option\_auditor/strategies/vertical\_spreads.py     |      140 |       28 |     80% |26, 32-37, 40-41, 47-48, 60, 70, 86-87, 119-124, 133-135, 158-159, 179, 192, 259-261 |
| option\_auditor/strategy.py                         |      256 |       33 |     87% |16, 35, 148-155, 204, 207-245, 279, 306 |
| option\_auditor/strategy\_metadata.py               |       37 |       11 |     70% |323, 325, 330-340 |
| option\_auditor/uk\_stock\_data.py                  |       41 |        8 |     80% |32-33, 52, 62, 67-69, 77 |
| option\_auditor/unified\_backtester.py              |       56 |        3 |     95% |44, 67, 85 |
| option\_auditor/unified\_screener.py                |      136 |       29 |     79% |38, 42-43, 49, 60-64, 79-82, 97-98, 121-124, 204-206, 217-223, 229, 246-249, 268-269 |
| option\_auditor/us\_stock\_data.py                  |        9 |        0 |    100% |           |
| webapp/\_\_init\_\_.py                              |        0 |        0 |    100% |           |
| webapp/app.py                                       |       80 |       14 |     82% |39-40, 78-81, 106-107, 111-112, 127-133 |
| webapp/blueprints/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| webapp/blueprints/analysis\_routes.py               |      171 |       12 |     93% |136-138, 176-184 |
| webapp/blueprints/journal\_routes.py                |       93 |        6 |     94% |40-42, 129-131 |
| webapp/blueprints/main\_routes.py                   |       65 |       13 |     80% |36-38, 44, 53-62, 70, 75-77, 91, 96 |
| webapp/blueprints/safety\_routes.py                 |       27 |        0 |    100% |           |
| webapp/blueprints/screener\_routes.py               |      473 |       67 |     86% |62-63, 110, 151, 202-203, 225-226, 232, 238-243, 250-251, 257, 264-267, 279, 285-288, 307, 327, 346, 365, 384, 404, 424, 443, 463-464, 496, 508, 527, 540-554, 560-572, 584, 602, 644, 657, 663-668 |
| webapp/blueprints/strategy\_routes.py               |        7 |        2 |     71% |     11-12 |
| webapp/cache.py                                     |       28 |        1 |     96% |        34 |
| webapp/schemas.py                                   |      120 |       12 |     90% |7, 37, 40-42, 50, 58, 61, 66-68, 85 |
| webapp/services/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| webapp/services/check\_service.py                   |       77 |       16 |     79% |54, 64, 72, 77-80, 87-94, 99-102 |
| webapp/services/scheduler\_service.py               |       38 |        0 |    100% |           |
| webapp/storage.py                                   |      412 |       33 |     92% |69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 113, 118, 278, 299, 329-330, 370-371, 411, 446-447, 466-469, 486, 503-504, 515, 527-528, 547 |
| webapp/utils.py                                     |       59 |        7 |     88% |32-33, 58-59, 69-71 |
| webapp/validation.py                                |       35 |        3 |     91% |     49-51 |
| **TOTAL**                                           | **8142** | **1088** | **87%** |           |


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