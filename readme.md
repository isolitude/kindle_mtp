## 标注文件格式

如果想要使用AI对标注的内容进行校正，我们需要获取相应的标注。其中在这个程序中，存放标注信息的文件是一个json，其具体格式如下

```json
{
    "书籍名称A": [
        {
            "location_start": 257,
            "text": "这是在书籍A中标注的第一段文字。"
        },
        {
            "location_start": 308,
            "text": "这是在书籍A中标注的第二段文字。"
        }
    ],
    "书籍名称B": [
        {
            "location_start": 1024,
            "text": "这是在书籍B中标注的文字。"
        }
    ]
}
```

其中，最外层以大括号包裹，其内部是由一个个字段组成，字段名称一般为书籍名称，书籍名称下，用中括号保存的是书籍对应的标注信息，其中每一个用大括号包裹。"location_start"字段表示该标注在书籍中的位置，可以是章节数，页数，字符数，如果是使用的kindle，就是其位置数。"text"字段表示标注的内容，也就是想要AI校正的部分。

#### Kindle的标注提取

对于在kindle阅读标注的用户，可以直接将kindle连接至电脑，使用程序 kindle_get_clipping.py 直接从kindle中读取"My Clippings.txt"文件（kindle需要解锁），并生成相应的标注文件"grouped_clipping.json"。



Kindle\_get\_clipping.py需要安装mtp库，具体的安装教程在附录，如果不想安装，手动将kindle连接至电脑后，找到Document文件夹，手动复制到当前目录，运行kindle\_get\_clipping\_nomtp.py，将其转换成"grouped\_clipping.json"

## 配置文件

在使用程序前，我们需要了解程序的配置文件config.json，其分为3个部分，对应校正的三个步骤。

### clippings_to_pre_correction

```json

"clippings_to_pre_correction" : {
    "clipping_json_path" : "grouped_clippings.json",
    "book_title_in_clipping" : "第三部",
    "book_path" : "第三部.txt",
    "locations" : {
        "start" : 1,
        "end" : 39000
    },
    "search_window_in_percentage" : 0.02,
    "pre_correction_json_path" : "pre_correction.json"
},
 
```

该字段对应的是查找到对应的标注所在txt文本中的位置，以及其所在的句子和对应的段落。



其中"clipping\_json\_path"是上面准备的标注文件的路径，"book\_title\_in\_clipping"是对应需要校正的书籍在标注文件中的书名，"book\_path"是对应书籍的txt文件路径。"locations"则是标注文件中"location\_start"的最大值与最小值，如果location代表的是章节，一般就是第一章和最后一章。对于kindle，需要手动打开书籍查看最后一页的位置



"search\_window\_in\_percentage" 是查找半径，是一个0到1之间的数，对于一个比较精确的location，比如字符数，可以将其设置的很小。如果是一个比较粗略的location，就需要设置的较大。对于kindle的"位置"，其不是很精确，一般在0.01到0.04之间。也就是查找location前后1%~4%字符数的文本



"pre_correction_json_path"是输出的路径，一般不需要改动

### pre_correction_to_correction

```json

"pre_correction_to_correction": {
    "llm_settings" : {
        "llm_api_url" : "https://api.easytransnote.com/v1/chat/completions",
        "llm_model" : "gemini-2.5-flash-preview-05-20",
        "llm_temperature" : 0.1,
        "llm_api_key" : "your key",
        "llm_prompt" : "your prompt",
        "task_per_request" : 20
    },
    "llm_settings_2": {
        "llm_api_url" : "https://api.easytransnote.com/v1/chat/completions",
        "llm_model" : "gemini-2.5-flash-preview-05-20",
        "llm_temperature" : 0.1,
        "llm_api_key" : "your key",
       `        "llm_prompt" : "your prompt 2",
        "task_per_request" : 10 
    },
    "pre_correction_json_path" : "pre_correction.json",
    "correction_json_path" : "correction.json",
    "re_correction_enabled" : true
    
},
```

这个字段是将标注内容，包括其上下文，发送给大模型的api，获取对应的校正意见的过程。



"llm_settings" 字段是初次处理对应的设置，其中"llm_api_url"，"llm_model"对应你的API提供商给的相应的访问网址和模型名称，一般来说使用Gemini比较稳定，其小参数模型在返回时可以稳定返回json，而openai的就有点不行。"llm_temperature"一般设置比较低，来获得稳定的返回，如果遇到模型不支持，此时设为1，"llm_api_key" 是你从API提供商获取的api key，此处不提供。



"llm_prompt"是对应的任务的提示词，在附录和实例文件中都有，此处就不重复了。如果想要修改提示词，建议将修改意见和提示词一并发给AI，让他修改。提示词中需要包含"INPUT_TASKS_JSON_STRING"字段，用于在程序中通过查找替换，将对应的标注内容替换进去。



"task_per_request" 是一次发送多少条标注，如果你发现在程序运行中很容易出现返回格式不正确导致的报错，可以将其改小一点。



"llm_prompt_2"是对于一句话中有其他的错误，或者有多个标注的额外处理，设置于上面基本相同，除了提示词需要修改，在对应的附录与实例文件中都有。



pre_correction_json_path，correction_json_path是程序的输入输出，一般不需要修改。



re_correction_enabled 一般来说，llm返回会有各种报错，会尝试再次发送给大模型

### correction_apply

```json
"correction_apply" : {
    "correction_json_path" : "correction.json",
    "book_path" : "第三部.txt",
    "output_path" : "第三部_corrected.txt"
}
```

这个字段将获得的校正信息，修正到原文处。"correction\_json\_path"是前文获得的校正信息，"book\_path"原文的txt，"output\_path"输出的txt

## 使用说明

### 获取相应的标注信息

参照上面的标注文件格式，利用程序生成一份标注文件。

### 查找标注在txt原文的位置

运行"clippings_to_pre_correction.py"，如果没能找到所有的标注文本的位置，可以设置更大的search_window_in_percentage，但是过大的search_window_in_percentage可能会导致匹配错误，标注匹配到不正确的位置上。



这个过程中会有几率标注对应的段落"paragraph"寻找到的结果不正确，一般是段落的结束符不在程序的已知列表里，不影响后续的操作。

运行之后得到的json样式为



### 发送标注及其上下文给大模型

运行"pre_correction_to_correction.py"，如果最后还是生成了"failed_corrections.json"，表示存在有标注校正失败，可以手动修改或者重新运行。

如果使用的模型不行，很容易出现json解析失败或者缺少对应的键值"keyerror"，导致程序报错退出，这一部分还在debug，会发布新代码修复。

### 根据校正信息，进行校对

运行"apply\_correction.py"，注意可能会有"原文与校正内容不匹配！，跳过校正。"的情况，此时检查下面输出的原文片段，可能是原文已经被校正过，此时可以忽略。

## 附录

## mtp库安装

使用的是这个库，一个老外写的，连个star都没有，不过不放心的话，手动复制kindle中的文件吧。

[https://github.com/Heribert17/mtp](https://github.com/Heribert17/mtp)

首先下载或clone这个库到本地，查看文件夹内容，如果没有src文件夹，就创建一个，将mtp和mtp.egg-info文件夹复制进去，在当前文件夹运行下面的代码安装

```bash

python -m pip install mtp
```
