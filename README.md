# NuGrade
NuGrade is a Flask-based tool for assessing the quality of nuclear data at a glance. It does this by comparing raw EXFOR data with evaluations. Error metrics such as absolute relative error or chi squared can be computed, capturing the deviation between evaluation and experiment. Energy coverage is also factored in, with reaction channels that are measured across a wide range of energy being scored better than those with only a few data points.

<img src="static/screenshots/chart_of_nuclides.png" width="800">


Specific reaction channels can be examined more closely.

<img src="static/screenshots/nuclide_lookup.png" width="400">

Claude is integrated with NuGrade, allowing for discussion of the computed metrics and analysis of the experimental corpus when available. The system is enhanced with retrieval-augmented generation that allows for specific sentences to be found. 

<img src="static/screenshots/chatbot_1.png" width="400">

<img src="static/screenshots/chatbot_2.png" width="400">



## Metric Options
|Parameter | Description |
|-----|--------|
|Lower Energy (eV)|The lower end of the energy range for which cross sections are scored|
|Upper Energy (eV)|The upper end of the energy range for which cross sections are scored|
|Log Scale|Whether energy coverage is considered on a linear or log scale|
|Width|How "wide" a measurement is considered in energy space when computing energy coverage|
|Metric|Which error metric to use for comparing EXFOR to evaluations. Absolute relative error is the simplest, while Chi squared factors in uncertainty.|
|Weighting|Flux function to weight the metric values by. High flux regions are the most important.|
|Evaluation|What evaluation to compare to.|

## Running a Local Copy
Due to the high volume of data needed to run this platform, this section is still under development while a more elegant solution for storage EXFOR and the various evaluations is considered.
### Pre-requisites 
The following packages are needed to run NuGrade locally:
- Numpy
- Pandas
- PyTorch 
- Bokeh
- Anthropic
- Markdown-it-py
- Transformers

### Installation
1. Clone the repo
```git clone https://github.com/iankolaja/NuGrade.git```
2. Install NuGrade
```python -m pip install .```
3. Add your Anthropic API key here (optional):
```keys/claude.txt```
4. Place nugrade_data.db:
```data/```
### Running
1. Run the top level script.
```python main.py```
2. Navigate to your web browser and open the locally hosted Flask application. Default local address: http://127.0.0.1:4000/
