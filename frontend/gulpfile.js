'use strict';

var gulp = require('gulp-help')(require('gulp'));
var $ = require('gulp-load-plugins')();
var del = require('del');
var runSequence = require('run-sequence');
var browserSync = require('browser-sync');
var reload = browserSync.reload;
var merge = require('merge-stream');
var path = require('path');
var fs = require('fs');
var glob = require('glob-all');
var historyApiFallback = require('connect-history-api-fallback');
var packageJson = require('./package.json');
var crypto = require('crypto');
var childProcess = require('child_process');
// var ghPages = require('gulp-gh-pages');

var AUTOPREFIXER_BROWSERS = [
  'ie >= 10',
  'ie_mob >= 10',
  'ff >= 30',
  'chrome >= 34',
  'safari >= 7',
  'opera >= 23',
  'ios >= 7',
  'android >= 4.4',
  'bb >= 10'
];

var targetApp = '';

var DIST = 'dist';

var dist = function(subpath) {
  switch (subpath) {
    case 'styles/' + targetApp:
      return path.join(DIST, 'static/frontend/', targetApp,'/styles');
    
    default:
      return !subpath ? DIST : path.join(DIST, subpath);
  }
};
var etoolsRoot = '../EquiTrack';
//var etoolsRoot = '..';
var etoolsAssets;
var etoolsAssetsPath;
var etoolsImages; 
var etoolsImagesPath;
var etoolsTemplatesPath;

var setGlobals = function() {
  // etoolsRoot = '../code';
  etoolsAssets = path.join(etoolsRoot, 'assets/frontend', targetApp);
  etoolsAssetsPath = path.join('static/frontend', targetApp);
  etoolsImages = path.join(etoolsRoot, 'assets/images');
  etoolsImagesPath = path.join(etoolsRoot, 'static/images');
  etoolsTemplatesPath = path.join(etoolsRoot, 'templates/frontend', targetApp);
};

// distribution folder structure
var etoolsDist = function(subpath, output) {
  switch (subpath) {
    case 'images':
      return etoolsImages;
    case 'elements':
      return !output ? path.join(etoolsAssets, 'elements') :
       path.join(etoolsAssetsPath, 'elements');
    case 'index':
      return etoolsTemplatesPath;
    case 'styles':
      return path.join(etoolsAssets, 'styles');
    case 'assets':
      return !output ? etoolsAssets : etoolsAssetsPath;
    case 'templates':
      return etoolsTemplatesPath;
    default:
      return !subpath ? etoolsAssets : path.join(etoolsAssets, subpath);
  }
};

// distribution path structure
var appPaths = function(path, output) {
  switch (path) {
    case 'elements':
      return !output ? 'elements/' + targetApp + '_elements.html' :
       '/' + etoolsDist('elements', true) + '/' + targetApp + '_elements.vulcanized.html';
    case 'images':
      return output ? etoolsImagesPath : etoolsImages;
  }
};

var styleTask = function(stylesPath, srcs) {
  return gulp.src(srcs.map(function(src) {
      return path.join('app', stylesPath, src);
    }))
    .pipe($.changed(stylesPath, {extension: '.css'}))
    .pipe($.autoprefixer(AUTOPREFIXER_BROWSERS))
    .pipe(gulp.dest('.tmp/' + stylesPath))
    .pipe($.minifyCss())
    .pipe(gulp.dest(dist(stylesPath)))
    .pipe($.size({title: stylesPath}));
};

var imageOptimizeTask = function(src, dest) {
  return gulp.src(src)
    .pipe($.imagemin({
      progressive: true,
      interlaced: true
    }))
    .pipe(gulp.dest(dest))
    .pipe($.size({title: 'images'}));
};

var optimizeHtmlTask = function(src, dest) {
  
  var assets = $.useref.assets({
    searchPath: ['.tmp', 'app', dist()]
  });

  // images are all common (indipendent of the app)
  var replaceImg =  function(imgStr) {
    return '/static/' + imgStr;
  };

  return gulp.src(src)
    // Replace path for vulcanized assets
    .pipe($.if('*.html', $.replace(appPaths('elements'), appPaths('elements', true))))
    // Replace image links
    .pipe($.if('*.html', $.replace('images/', replaceImg)))
    .pipe(assets)
    // Concatenate and minify JavaScript
    .pipe($.if('*.js', $.uglify({
      preserveComments: false
    })))
    // Concatenate and minify styles
    // In case you are still using useref build blocks
    .pipe($.if('*.css', $.minifyCss()))
    .pipe(assets.restore())
    .pipe($.useref())
    // Minify any HTML
    .pipe($.if('*.html', $.minifyHtml({
      quotes: true,
      empty: true,
      spare: true
    })))
    // Output files
    .pipe(gulp.dest(dest))
    .pipe($.size({
      title: 'html'
    }));
};

// Compile and automatically prefix stylesheets
gulp.task('styles', function() {
  return styleTask('styles/' + targetApp, ['**/*.css']);
});

gulp.task('elements', function() {
  return styleTask('elements', ['**/*.css']);
});

// Lint JavaScript
gulp.task('lint', function() {
  return gulp.src([
      'app/scripts/**/*.js',
      'app/elements/**/*.js',
      'app/elements/**/*.html',
      'gulpfile.js'
    ])
    .pipe(reload({
      stream: true,
      once: true
    }))

  // JSCS has not yet a extract option
  .pipe($.if('*.html', $.htmlExtract()))
  .pipe($.jshint())
  .pipe($.jscs())
  .pipe($.jscsStylish.combineWithHintResults())
  .pipe($.jshint.reporter('jshint-stylish'))
  .pipe($.if(!browserSync.active, $.jshint.reporter('fail')));
});

// Optimize images
gulp.task('images', function() {
  return imageOptimizeTask('app/images/**/*', dist('images'));
});

// Copy all files at the root level (app)
gulp.task('copy', function() {
  var app = gulp.src([
    'app/*',
    '!app/test',
    '!app/cache-config.json'
  ], {
    dot: true
  }).pipe(gulp.dest(dist()));

  var bower = gulp.src([
    'bower_components/**/*'
  ]).pipe(gulp.dest(dist('bower_components')));

  var elements = gulp.src(['app/elements/**/*.html',
      'app/elements/**/*.css',
      'app/elements/**/*.js'
    ])
    .pipe(gulp.dest(dist('elements')));

  var swBootstrap = gulp.src(['bower_components/platinum-sw/bootstrap/*.js'])
    .pipe(gulp.dest(dist('elements/bootstrap')));

  var swToolbox = gulp.src(['bower_components/sw-toolbox/*.js'])
    .pipe(gulp.dest(dist('sw-toolbox')));

  var vulcanized = gulp.src(['app/elements/' + targetApp + '_elements.html'])
    .pipe($.rename(targetApp + '_elements.vulcanized.html'))
    .pipe(gulp.dest(dist('elements')));

  return merge(app, bower, elements, vulcanized, swBootstrap, swToolbox)
    .pipe($.size({
      title: 'copy'
    }));
});

// Copy web fonts to dist
gulp.task('fonts', function() {
  return gulp.src(['app/fonts/**'])
    .pipe(gulp.dest(dist('fonts')))
    .pipe($.size({
      title: 'fonts'
    }));
});

// Scan your HTML for assets & optimize them
gulp.task('html', function() {
  return optimizeHtmlTask(
    ['app/**/*.html', '!app/{elements,test}/**/*.html'],
    dist());
});

// Vulcanize granular configuration
gulp.task('vulcanize', function() {
  var DEST_DIR = dist(etoolsDist('elements', true));
  return gulp.src(dist('elements/' + targetApp + '_elements.vulcanized.html'))
    .pipe($.vulcanize({
      stripComments: true,
      inlineCss: true,
      inlineScripts: true
    }))
    .pipe(gulp.dest(DEST_DIR))
    .pipe($.size({title: 'vulcanize'}));
});

// Generate config data for the <sw-precache-cache> element.
// This include a list of files that should be precached, as well as a (hopefully unique) cache
// id that ensure that multiple PSK projects don't share the same Cache Storage.
// This task does not run by default, but if you are interested in using service worker caching
// in your project, please enable it within the 'default' task.
// See https://github.com/PolymerElements/polymer-starter-kit#enable-service-worker-support
// for more context.
gulp.task('cache-config', function(callback) {
  var dir = dist();
  var config = {
    cacheId: packageJson.name || path.basename(__dirname),
    disabled: false
  };

  glob([
    targetApp + '.html',
    './',
    'bower_components/webcomponentsjs/webcomponents-lite.min.js',
    '{elements,scripts,styles}/**/*.*'],
    {cwd: dir}, function(error, files) {
    if (error) {
      callback(error);
    } else {
      config.precache = files;

      var md5 = crypto.createHash('md5');
      md5.update(JSON.stringify(config.precache));
      config.precacheFingerprint = md5.digest('hex');

      var configPath = path.join(dir, 'cache-config.json');
      fs.writeFile(configPath, JSON.stringify(config), callback);
    }
  });
});

// Clean output directory
gulp.task('clean', function() {
  return del(['.tmp', dist()]);
});

// Watch files for changes & reload
gulp.task('serve', ['styles', 'elements', 'images'], function() {

  //TODO:  set the target app at this point

  var dataMiddleware = function(req, res, next) {
    switch (req.url){
      // common resources
      case '/index.html':
        req.url = '/' + targetApp + '.html';
        break;      
      case '/users/api/profile/':
        req.url = '/data/users/profile.json';
        break;

      // management app
      case '/management/api/stats/usercounts/':
        req.url = '/data/users/usercounts.json';
        break;
      case '/management/api/stats/trips/':
        req.url = '/data/management/tripsstats.json';
        break;
      case '/management/api/stats/agreements/':
        req.url = '/data/management/agreementsstats.json';
        break;
      case '/management/api/stats/interventions/':
        req.url = '/data/management/interventionsstats.json';
        break;

      // partner app
      case '/api/interventions/':
        req.url = '/data/partner/interventions.json';
        break;
      case '/locations/autocomplete/?q=as':
        req.url = '/data/partner/locationsautocomplete.json';
        break;
      case '/api/interventions/7/':
        req.url = '/data/partner/intervention_details.json';
        break;
      case '/api/interventions/7/results/201/':
        req.url = '/data/partner/resultchain_details.json';
        break;
    }
    return next();
  };

  browserSync({
    port: 5000,
    notify: false,
    logPrefix: 'PSK',
    snippetOptions: {
      rule: {
        match: '<span id="browser-sync-binding"></span>',
        fn: function(snippet) {
          return snippet;
        }
      }
    },
    // Run as an https by uncommenting 'https: true'
    // Note: this uses an unsigned certificate which on first access
    //       will present a certificate warning in the browser.
    // https: true,
    server: {
      baseDir: ['.tmp', 'app'],
      middleware: [historyApiFallback(), dataMiddleware],
      routes: {
        '/bower_components': 'bower_components',
        '/data': 'data'
      }
    }
  });

  gulp.watch(['app/**/*.html']);
  gulp.watch(['app/styles/**/*.css'], ['styles']);
  gulp.watch(['app/elements/**/*.css'], ['elements']);
  gulp.watch(['app/{scripts,elements}/**/{*.js,*.html}'], ['lint']);
  gulp.watch(['app/images/**/*']);
});

// Build and serve the output from the dist build
gulp.task('serve:dist', ['buildFront:partner', 'buildFront:management'], function() {
  // browserSync({
  //   port: 5001,
  //   notify: false,
  //   logPrefix: 'PSK',
  //   snippetOptions: {
  //     rule: {
  //       match: '<span id="browser-sync-binding"></span>',
  //       fn: function(snippet) {
  //         return snippet;
  //       }
  //     }
  //   },
  //   // Run as an https by uncommenting 'https: true'
  //   // Note: this uses an unsigned certificate which on first access
  //   //       will present a certificate warning in the browser.
  //   // https: true,
  //   server: dist(),
  //   middleware: [historyApiFallback()]
  // });
  var reloadDist = ['buildFront:partner', 'buildFront:management'];

  gulp.watch(['app/**/*.html', '!app/bower_components/**/*.html'], reloadDist);
  gulp.watch(['app/styles/**/*.css'], reloadDist);
  gulp.watch(['app/elements/**/*.css'],  reloadDist);
  gulp.watch(['app/scripts/**/*.js'], reloadDist);
  gulp.watch(['app/images/**/*'], reloadDist);
});

// Build production files, the default task
gulp.task('default', ['clean'], function(cb) {
  // Uncomment 'cache-config' if you are going to use service workers.
  runSequence(
    ['copy', 'styles'],
    'elements',
    ['lint', 'images', 'fonts', 'html'],
    'vulcanize', // 'cache-config',
    cb);
});

// Build then deploy to GitHub pages gh-pages branch
gulp.task('build-deploy-gh-pages', function(cb) {
  runSequence(
    'default',
    'deploy-gh-pages',
    cb);
});

// Deploy to GitHub pages gh-pages branch
gulp.task('deploy-gh-pages', function() {
  return gulp.src(dist('**/*'))
    // Check if running task from Travis Cl, if so run using GH_TOKEN
    // otherwise run using ghPages defaults.
    .pipe($.if(process.env.TRAVIS === 'true', $.ghPages({
      remoteUrl: 'https://$GH_TOKEN@github.com/polymerelements/polymer-starter-kit.git',
      silent: true,
      branch: 'gh-pages'
    }), $.ghPages()));
});

gulp.task('movehtml', function() {
  var DEST_DIR = dist('templates/frontend/' + targetApp);

  return gulp.src('app/*.html')
    .pipe(gulp.dest(DEST_DIR));
});

gulp.task('buildDist', ['clean'], function(cb) {
  // Uncomment 'cache-config' if you are going to use service workers.
  runSequence(
    ['copy', 'styles'],
    'elements',
    ['lint', 'images', 'fonts', 'html'],
    'vulcanize', // 'cache-config',
    cb);
});

// copy over the distribution files for app
gulp.task('frontendBuild', ['buildDist'], function() {
  gulp.src('dist/' + targetApp + '.html')
  // .pipe($.rename('index.html'))
  .pipe(gulp.dest(etoolsDist('index')));

  gulp.src('dist/static/**/*')
  .pipe(gulp.dest(path.join(etoolsRoot, 'assets')));

});

gulp.task('buildFront:partner', function(cb) {
  targetApp = 'partner';
  setGlobals();
  runSequence('frontendBuild', cb);
});

gulp.task('buildFront:management', function(cb) {
  targetApp = 'management';
  setGlobals();
  runSequence('frontendBuild', cb);
});

gulp.task('serve:management', function(cb) {
  targetApp = 'management';
  setGlobals();
  runSequence('serve', cb);
});
gulp.task('serve:partner', function(cb) {
  targetApp = 'partner';
  setGlobals();
  runSequence('serve', cb);
});

// web component test (polymer unit test)
gulp.task('wct:browser', function() {
  gulp.src(__filename)
    .pipe($.open({uri: 'http://127.0.0.1:2000/components/frontend/app/test/index.html'}));
});

gulp.task('wct:livereload', function() {  
  var child = childProcess.exec('./node_modules/livereloadx/bin/livereloadx.js app/test/');
  child.stdout.on('data', function(data) {
    console.log(data.replace(/[\n\r]+/g, ''));
  });
});

gulp.task('wct:start', function() {  
  var child = childProcess.exec('./node_modules/web-component-tester/bin/wct -p');
  child.stdout.on('data', function(data) {
    console.log(data.replace(/[\n\r]+/g, ''));
  });
});

gulp.task('wct:test:local', function(cb) {
  runSequence(
    'wct:start',
    'wct:browser',
    'wct:livereload',
    cb
  );
});

// Load tasks for web-component-tester
// Adds tasks for `gulp test:local` and `gulp test:remote`
require('web-component-tester').gulp.init(gulp);

// Load custom tasks from the `tasks` directory
try {
  require('require-dir')('tasks');
} catch (err) {}
