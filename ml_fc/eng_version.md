Well water cut calculation using Machine Learning
#### Alexander Kalinichenko

This notebook demonstrates how to train a machine learning algorithm to predict water cut (WCT) of oil production wells.
The exercise is based on data of a field in Russia, Volga-Ural basin.

_Add some info about field..._

The dataset was created from observed production data from 70 wells which was combined with other well bore data such as bottom location, perforation interval, well bore type, well operation duration etc. This data uses to train Random Forresr Regression to predict water cut of producing wells or planned side-tracks. The sklearn.ensemble module was used in this exercise. The [enseble methods](https://scikit-learn.org/stable/modules/classes.html#module-sklearn.ensemble) includes ensemble-based methods for classification, regression and anomaly detection from [scikit-learn Python library](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html). A random forest is a meta estimator that fits a number of classifying decision trees on various sub-samples of the dataset and uses averaging to improve the predictive accuracy and control over-fitting. A random forest regresor was choosen because this is simple, easy undenstandable without over-fitting algorithm.

First we will [explore the dataset](#Exploring-the-dataset).  We will load the training data from 70 wells, and take a look at what we have to work with.  We will plot the location data , and create cross plots to look at the variation within the data.  

. . .



## Hypothesis:
- Cummulative oil production depend on well location
- Wells with maximum total oil production are located in the top of reservoir. There is a line of best well positions. This line may be located not in the center of structure created for geomodel. So, remaining oil well production could be calculated using well coordinates.

**Main goal:**

- Estimate chances of succes for drilling additional side-tracks

**Additional goals**:
- Forecast water cut
- Forecast additional oil production
- Forecast oil-water contact