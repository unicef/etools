(function () {
'use strict';

var gulp = require('gulp-help')(require('gulp'));
var $ = require('gulp-load-plugins')();
var _ = require('lodash');

var browserSync = require('browser-sync');
var childProcess = require('child_process');
var del = require('del');
var faker = require('faker');
var pg = require('pg');
var reload = browserSync.reload;
var runSequence = require('run-sequence');

var FILTER_COUNT = 5;

gulp.task('clean', function () {
  return del([
    'node_modules/',
  ]);
});

gulp.task('livereload', function() {
  var child = childProcess.exec('./node_modules/livereloadx/bin/livereloadx.js ../EquiTrack');
  child.stdout.on('data', function(data) {
    console.log(data.replace(/[\n\r]+/g, ''));
  });
});

gulp.task('default', function(cb) {
  runSequence(
    'livereload',
    cb);
});

var conString = 'postgres://postgres:password@localhost:5432/test_db';
var client = new pg.Client(conString);

gulp.task('postgres:load_data', function(){
  client.connect(function(err) {
      client.query('SET search_path TO hoth');
      var query = '';

      client.query('DELETE FROM reports_resultstructure');
      for (var i=1; i<FILTER_COUNT + 1; i++) {
        query = client.query("INSERT INTO reports_resultstructure (id, name, from_date, to_date) VALUES (" + i + ", '" + faker.company.companyName() +  "', '2001-01-01', '2001-01-01')");
      }

      client.query('DELETE FROM reports_sector');
      for (var i=1; i<FILTER_COUNT + 1; i++) {
        query = client.query("INSERT INTO reports_sector (id, name, dashboard) VALUES (" + i + ", '" + faker.company.catchPhrase() +  "', true)");
      }

      client.query('DELETE FROM locations_gatewaytype');
      for (var i=1; i<FILTER_COUNT + 1; i++) {
        query = client.query("INSERT INTO locations_gatewaytype (id, name) VALUES (" + i + ", '" + faker.name.firstName() +  "')");
      }

      client.query('DELETE FROM funds_donor');
      for (var i=1; i<FILTER_COUNT + 1; i++) {
        query = client.query("INSERT INTO funds_donor (id, name) VALUES (" + i + ", '" + faker.company.companyName() +  "')");
      }

      client.query('DELETE FROM partners_partnerorganization');
      for (var i=1; i<FILTER_COUNT + 1; i++) {
        query = client.query("INSERT INTO partners_partnerorganization (id, vision_synced, partner_type, shared_partner, name, short_name, description) VALUES (" + i + ", true, '" + faker.name.lastName() +  "', '" + faker.firstNameFemale +  "', '" + faker.name.firstName() +  "', '" + faker.lorem.words() +  "', '" + faker.lorem.words() + "')");
      }

      query.on('end', function(result) {
        client.end();
      })
    });
})

// web component test (polymer unit test)
gulp.task('wct:browser', function() {
  gulp.src('../EquiTrack')
    .pipe($.open({uri: 'http://127.0.0.1:2000/test/index.html'}));
});

gulp.task('wct:livereload', function() {
  var child = childProcess.exec('./node_modules/livereloadx/bin/livereloadx.js ../EquiTrack/test/');
  child.stdout.on('data', function(data) {
    console.log(data.replace(/[\n\r]+/g, ''));
  });
});

gulp.task('wct:start', function() {
  var child = childProcess.exec('./node_modules/web-component-tester/bin/wct -p --root ../EquiTrack');
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

}());