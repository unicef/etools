<h2 id="getting-your-development-environment-working">Getting your development environment working:</h2>



<h4 id="setting-up-the-server">Setting up the server:</h4>

<p>Step 1: </p>

<blockquote>
  <p>Install Postgresql with brew:</p>
  
  <blockquote>
    <p>$<code>brew install postgresql</code></p>
  </blockquote>
  
  <p>Create your database:</p>
  
  <blockquote>
    <p>$<code>initdb /usr/local/var/postgres</code></p>
  </blockquote>
  
  <p>Make it run on startup</p>
  
  <blockquote>
    <p>$<code>mkdir -p ~/Library/LaunchAgents</code> <br>
    $<code>ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents</code> <br>
    $<code>launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist</code></p>
  </blockquote>
</blockquote>

<p>Step 2:</p>

<blockquote>
  <p>Install Postgis:</p>
  
  <blockquote>
    <p>$<code>brew install postgis</code></p>
  </blockquote>
  
  <p>Connect to db:</p>
  
  <blockquote>
    <p>$<code>psql postgres</code></p>
  </blockquote>
  
  <p>Create user postgres:</p>
  
  <blockquote>
    <p>#<code>CREATE ROLE postgres WITH superuser login;</code></p>
  </blockquote>
  
  <p>Create postgis necessary extensions:</p>
  
  <blockquote>
    <p>#<code>CREATE EXTENSION postgis;</code> <br>
    #<code>CREATE EXTENSION postgis_topology;</code> <br>
    #<code>CREATE EXTENSION fuzzystrmatch;</code> <br>
    #<code>\q</code> -&gt; to exit</p>
  </blockquote>
</blockquote>

<p>Step 3:</p>

<blockquote>
  <p>Install Redis:</p>
  
  <blockquote>
    <p>$<code>brew install redis</code></p>
  </blockquote>
</blockquote>

<p>Step 4:</p>

<blockquote>
  <p>Install <a href="https://virtualenv.pypa.io/en/latest/">VirtualEnv</a> and <a href="http://virtualenvwrapper.readthedocs.org/en/latest/">VirtualEnvWrapper</a> <br>
  Once inside the virtual environment install the requirements found at <code>EquiTrack/requirements/base.txt</code></p>
  
  <blockquote>
    <p>$<code>pip install -f [path_to_file]/base.txt</code></p>
  </blockquote>
</blockquote>

<p>Step 5:</p>

<blockquote>
  <p>Set up the following environment variables:</p>
  
  <blockquote>
    <p>$<code>export REDIS_URL=redis://localhost:6379/0</code> <br>
    $<code>export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres</code> <br>
    $<code>export DJANGO_DEBUG=true</code></p>
  </blockquote>
</blockquote>

<p>Step 6:</p>

<blockquote>
  <p>While inside the virtual environment (after making sure the app can run ./manage.py runserver 8080) tackle the migrations:</p>
  
  <blockquote>
    <p>$<code>python manage.py migrate_schemas --fake-initial</code></p>
  </blockquote>
</blockquote>

<p>Step 7:</p>

<blockquote>
  <p>Time to create a superuser:</p>
  
  <blockquote>
    <p><code>python manage.py createsuperuser</code></p>
  </blockquote>
</blockquote>

<h4 id="setting-up-the-debugger-with-pycharm">Setting up the debugger with PyCharm</h4>

<p>Step 1:</p>

<blockquote>
  <p>Once the project is loaded in PyCharm go to menu -&gt; <code>PyCharm - &gt; Preferences -&gt; Project</code> <br>
  Make sure your project is chosen <br>
  Select the python interpreter present inside of the virtualenvironment</p>
</blockquote>

<p>Step 2:</p>

<blockquote>
  <p>Go to menu -&gt; <code>PyCharm - &gt; Preferences -&gt; Languages &amp; Frameworks -&gt; Django</code> <br>
  Select your project and: <br>
   * enable Django Support <br>
    * Set Django Project root <br>
    * choose base.py as the settings file <br>
    * add all of the previously mentioned environment vars</p>
</blockquote>

<p>Step 3:</p>

<blockquote>
  <p>Go to menu -&gt; <code>Run -&gt; Edit Configurations</code> <br>
  Add Django Server and name it. <br>
  In the Configuration make sure to add the environment variables again <br>
  Choose the python interpreter (The interpreter inside of the virtual environment) <br>
  Choose a working Directory</p>
</blockquote>

<p>Step 4:</p>

<blockquote>
  <p>Quit Pycharm and restart it… Voila!</p>
</blockquote>

<h4 id="resources">Resources:</h4>

<p><a href="http://www.gotealeaf.com/blog/how-to-install-postgresql-on-a-mac">http://www.gotealeaf.com/blog/how-to-install-postgresql-on-a-mac</a></p>

<p><a href="http://jasdeep.ca/2012/05/installing-redis-on-mac-os-x/">http://jasdeep.ca/2012/05/installing-redis-on-mac-os-x/</a></p>

<p><a href="https://virtualenv.pypa.io/en/latest/userguide.html">https://virtualenv.pypa.io/en/latest/userguide.html</a></p>

<p><a href="https://www.jetbrains.com/pycharm/help/run-debug-configuration.html">https://www.jetbrains.com/pycharm/help/run-debug-configuration.html</a></p>

<p><a href="http://postgis.net/install">http://postgis.net/install</a></p>

<p><a href="http://virtualenvwrapper.readthedocs.org/en/latest/index.html">http://virtualenvwrapper.readthedocs.org/en/latest/index.html</a></p>
