# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |       57 |      0% |     1-101 |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   425-426 |
| option\_auditor/common/data\_utils.py      |      185 |       39 |     79% |24-25, 48-51, 77-81, 88-89, 93-97, 101-102, 106-107, 118-119, 157, 199-201, 213, 216-218, 235-237, 246-248, 300-301 |
| option\_auditor/common/resilience.py       |       10 |        0 |    100% |           |
| option\_auditor/common/signal\_type.py     |        6 |        0 |    100% |           |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py      |       32 |        5 |     84% |     40-45 |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       50 |     91% |94-95, 190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/master\_screener.py        |      249 |       64 |     74% |47-51, 69-71, 82-83, 97, 99-100, 112-113, 123-136, 151-153, 168-169, 182, 191-193, 210, 241, 250-255, 263-267, 270-272, 284-294, 300, 321-322, 345-346, 372-374, 379 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      269 |       16 |     94% |12, 33-38, 156, 192, 201, 205, 207-208, 330-331, 340 |
| option\_auditor/portfolio\_risk.py         |      104 |       15 |     86% |63-66, 76-78, 82, 89, 118-125, 196 |
| option\_auditor/quant\_engine.py           |      152 |      134 |     12% |14-65, 73-91, 99-142, 149-158, 166-188, 195-232, 240-270 |
| option\_auditor/screener.py                |     1668 |      352 |     79% |13-14, 40-41, 56-58, 70-72, 74, 95-142, 150, 162-164, 177, 183, 200-201, 223-226, 228-231, 252-256, 261-263, 276, 317-319, 327, 332, 350-351, 364-365, 371, 420-422, 476, 479, 552-555, 557-560, 562-565, 567-568, 570-571, 584-588, 593-595, 625-626, 629, 719-720, 747-750, 752-755, 757-760, 762-763, 765-766, 776-782, 787-789, 837-839, 867-877, 887-890, 907, 942-944, 982-985, 987-990, 992-995, 997-998, 1000-1001, 1011-1017, 1022-1024, 1040, 1105, 1108-1109, 1121-1125, 1128, 1131-1132, 1169-1171, 1181-1183, 1217, 1264-1265, 1267-1269, 1277-1279, 1389-1390, 1410-1412, 1423-1425, 1493, 1535-1536, 1571, 1580, 1659-1661, 1671, 1718-1721, 1725, 1765, 1777, 1797, 1852-1853, 1877, 1883, 1919-1921, 1957-1958, 2011-2012, 2023, 2118-2119, 2133-2134, 2141-2142, 2155-2156, 2165, 2167, 2173-2174, 2180, 2218, 2233, 2244, 2321-2322, 2339-2341, 2347-2349, 2357-2359, 2371-2372, 2405, 2412-2419, 2425, 2427, 2429, 2438-2440, 2459, 2467-2469, 2486-2487, 2505-2506, 2538, 2548-2599, 2623, 2640, 2645, 2678-2679, 2684-2685, 2715, 2734-2736, 2742-2743, 2747-2750, 2756, 2758, 2765, 2767, 2769, 2771, 2784-2786, 2810-2811, 2850, 2875-2876, 2916-2918 |
| option\_auditor/sp500\_data.py             |       34 |        5 |     85% |31-32, 50-53 |
| option\_auditor/strategies/\_\_init\_\_.py |        6 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |       17 |        4 |     76% |12, 20, 29-30 |
| option\_auditor/strategies/fourier.py      |       42 |       24 |     43% |11-44, 48, 54, 65-66 |
| option\_auditor/strategies/grandmaster.py  |       49 |       13 |     73% |29, 50-57, 117-124 |
| option\_auditor/strategies/isa.py          |       35 |        3 |     91% | 21, 76-78 |
| option\_auditor/strategies/turtle.py       |       34 |        4 |     88% | 17, 44-46 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py         |       26 |        5 |     81% |     38-43 |
| option\_auditor/unified\_backtester.py     |      236 |       19 |     92% |35-37, 44, 168, 241-242, 252-253, 257-258, 261-262, 279-284, 335-336 |
| option\_auditor/unified\_screener.py       |      146 |       97 |     34% |40-83, 93-221, 241-248, 256, 271-275, 297-298, 306 |
| option\_auditor/us\_stock\_data.py         |       21 |       15 |     29% |     50-73 |
| webapp/app.py                              |      889 |      253 |     72% |41-42, 81, 87, 102, 104, 107, 109, 151-152, 253-254, 294, 308-310, 329-344, 358-359, 369-370, 408-410, 426-427, 431, 461-463, 467-480, 493-494, 500-501, 508-509, 516-518, 529, 533, 535, 537, 547-549, 561, 565, 567, 569, 571, 595, 599, 601, 605, 607-609, 615-617, 629, 633, 635, 637, 639, 647-649, 661, 665, 669, 671, 673-675, 681-683, 702-704, 719, 726-755, 759-788, 798, 827-829, 843, 847, 853-854, 865, 871-876, 893-898, 901-902, 920, 929, 931, 935-962, 965-970, 974-976, 991, 1001-1003, 1042-1043, 1068-1070, 1078-1090, 1109-1111, 1118-1119, 1141-1149, 1237-1243 |
| webapp/main.py                             |       20 |       20 |      0% |      1-35 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                  | **5771** | **1279** | **78%** |           |


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