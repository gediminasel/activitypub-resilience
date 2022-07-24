# Part II project, Cambridge Bachelor's degree <br/> Improving Resilience of ActivityPub Services

By Gediminas Lelešius, g@lelesius.eu

This repository contains implementations of the lookup server and the verifier,
as well as some tools and scripts used for testing.

**The code isn't ready for production use adn provided without warranty of any kind.**
See [License](LICENSE) for more details.

## [Dissertation](dissertation.pdf)
Differs from the dissertation submitted for the Degree, see Notice in the cover.


### Notice

This repository does not contain all the code submitted for the Examination.  
[Modified Mastodon code can be found here](https://github.com/gediminasel/mastodon-resilience).  

### Prerequisites

Install Python 3.9+ (tested with 3.9 and 3.10)

### Developing

Install requirements  
```pip install -r requirements.txt -r requirements_dev.txt```

### Running

Install requirements  
```pip install -r requirements.txt```

Configure respective config file  
```res/verifier/config.json``` or ```res/lookup/config.json```

Run lookup or verifier  
```python run.py -h```

#### Lookup
```python run.py lookup --from URI1 --from URI2 ...```

#### Verifier
```python run.py verifier --watch URI1 --watch URI2```