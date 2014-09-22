# tii lti launch tool ##

This is a simple launch tool to launch a Turnitin LTI instance.

It supports using custom Tii LTI extensions

It is based on [lti_tool_consumer_example_flask](https://github.com/tophatmonocle/lti_tool_consumer_example_flask)

## Dependencies ##

 * [ims-lti-py](https://github.com/tophatmonocle/ims-lti-py)
 * [Flask](https://github.com/mitsuhiko/flask)

## Installation ##

* install dependencies
* clone this repository
* change consumer_key and consumer_secret to the right values in `tool_consumer.py`

## Usage ##

* if you want to run it as normal user bound to the local machine, change (at the end of the `tool_consumer.py` file) `app.run(host='0.0.0.0', port = 80)` to `app.run()`
* if not, you have to run it as root: `sudo python tool_consumer.py`
* point your browser to `where-you-installed-it.com/first`
* change the parameters, click *submit*
* you can access the results of the extensions with the links at the top. A click on one of the links takes you back to the submission page with the URL filled in as *launch_url*

## FAQ ##

### Why do you use POST requests where you should be using GET? ###

This is a workaround as flask doesn't allow a *Content-Type* header in a GET request, but Tii currently (7/2014) expects it to be there. On the other hand, Tii doesn't test if it's a POST or GET request, so POST is used.

### What is my_tool_consumer.py? ###

A subclass of the *ims-lti-py* ToolConsumer that fixes some bugs present in the original class.
