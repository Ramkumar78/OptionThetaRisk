# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |        0 |    100% |           |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   458-459 |
| option\_auditor/common/data\_utils.py      |      142 |       36 |     75% |19-20, 36, 58-64, 71-72, 76-80, 87-88, 92-93, 105-106, 117-118, 148, 192-194, 206, 209-211, 228-230, 239-241 |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py      |        9 |        0 |    100% |           |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       48 |     92% |190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      266 |       16 |     94% |12, 33-38, 155, 191, 200, 204, 206-207, 328-329, 338 |
| option\_auditor/screener.py                |     1412 |      339 |     76% |22-23, 76-77, 90-92, 123, 125, 128-129, 149, 151, 155-158, 168, 180-182, 201-204, 221-222, 232-233, 249-252, 254-257, 286-298, 303-305, 319, 375-377, 390, 395, 413-414, 427-428, 434, 478-480, 534, 537, 635-638, 640-643, 645-648, 650-651, 653-654, 664-671, 676-678, 707-708, 711, 746-749, 786-787, 814-817, 819-822, 824-827, 829-830, 832-833, 843-849, 854-856, 897-899, 915-918, 927-937, 941-944, 947-950, 977-979, 1018-1021, 1023-1026, 1028-1031, 1033-1034, 1036-1037, 1047-1053, 1058-1060, 1084, 1147-1161, 1175-1185, 1196-1258, 1266-1269, 1308, 1372-1373, 1375-1377, 1386-1388, 1416, 1565-1566, 1582-1584, 1595-1597, 1658, 1732, 1763-1764, 1861-1862, 1895-1897, 1953, 1960-1961, 2003, 2009, 2064-2066, 2163-2164, 2198-2199, 2216-2217, 2219, 2245-2246, 2261-2262, 2269-2270, 2283-2284, 2297, 2299, 2306-2307, 2313, 2354, 2477-2478, 2503-2505, 2507-2509, 2511-2513, 2524-2526, 2540-2541, 2573-2575, 2588-2598, 2613-2615, 2628, 2639, 2648-2650, 2665-2666, 2668-2669, 2690-2691, 2718, 2728-2774 |
| option\_auditor/sp500\_data.py             |        4 |        1 |     75% |        11 |
| option\_auditor/strategies/\_\_init\_\_.py |        3 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |        6 |        1 |     83% |        12 |
| option\_auditor/strategies/fourier.py      |       42 |        8 |     81% |48, 54, 61-66 |
| option\_auditor/strategies/isa.py          |       27 |        4 |     85% |     34-37 |
| option\_auditor/strategies/turtle.py       |       34 |        2 |     94% |     8, 17 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py         |        3 |        0 |    100% |           |
| option\_auditor/unified\_screener.py       |      114 |       33 |     71% |22-24, 35, 42-44, 47, 64, 97-98, 105-106, 112-113, 132-134, 143, 177, 183-201 |
| webapp/app.py                              |      603 |      117 |     81% |85-86, 208, 220-221, 239-240, 247, 280, 295-296, 311-312, 317, 350-351, 360, 401, 405, 407, 419-420, 431, 435, 437, 439, 461, 465, 467, 472-474, 479-480, 491, 495, 497, 499, 508-509, 521, 525, 529, 533-535, 540-541, 545-557, 567, 582, 586, 588, 590, 593-595, 600-601, 605-635, 650, 659-660, 702-703, 730-731, 750-752, 759-760, 782-790, 876-882 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                  | **4206** |  **690** | **84%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://github.com/Ramkumar78/OptionThetaRisk/raw/python-coverage-comment-action-data/badge.svg)](https://github.com/Ramkumar78/OptionThetaRisk/tree/python-coverage-comment-action-data)

This is the one to use if your repository is private or if you don't want to customize anything.



## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.