/* 
  conf options:
    https://github.com/Polymer/web-component-tester/blob/master/runner/config.js
*/

var path = require('path');

var conf = {
  'expanded' : true,
  'suites': ['app/test/index.html'],
  'webserver': {
    'pathMappings': []
  },
  'plugins': {
    'local': {
      'browsers': ['chrome']
    }
  }
};

var mapping = {};
var rootPath = (__dirname).split(path.sep).slice(-1)[0];

mapping['/components/' + rootPath  +
'/app/bower_components'] = 'bower_components';

conf.webserver.pathMappings.push(mapping);

module.exports = conf;
