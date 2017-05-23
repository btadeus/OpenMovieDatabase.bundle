API_URL = 'http://www.omdbapi.com/?apikey=%s&i=%s&plot=%s&tomatoes=true'
RE_RUNTIME = Regex('((?P<hours>[0-9]+) hrs? )?(?P<minutes>[0-9]+) min')

def Start():

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10) AppleWebKit/600.1.25 (KHTML, like Gecko) Version/8.0 Safari/600.1.25'
  HTTP.Headers['Referer'] = 'http://www.imdb.com/'

def ValidatePrefs():

  pass

class OmdbApi(Agent.Movies):

  name = 'Open Movie Database'
  languages = [Locale.Language.English]
  primary_provider = False
  contributes_to = [
    'com.plexapp.agents.imdb',
    'com.plexapp.agents.themoviedb'
  ]

  def search(self, results, media, lang):

    if media.primary_agent == 'com.plexapp.agents.imdb':

      imdb_id = media.primary_metadata.id

    elif media.primary_agent == 'com.plexapp.agents.themoviedb':

      # Get the IMDb id from the Movie Database Agent
      imdb_id = Core.messaging.call_external_function(
        'com.plexapp.agents.themoviedb',
        'MessageKit:GetImdbId',
        kwargs = dict(
          tmdb_id = media.primary_metadata.id
        )
      )

      if not imdb_id:
        Log("*** Could not find IMDb id for movie with The Movie Database id: %s ***" % (media.primary_metadata.id))
        return None

    results.Append(MetadataSearchResult(
      id = imdb_id,
      score = 100
    ))

  def update(self, metadata, media, lang):

    if Prefs['plot']:
      plot = Prefs['plot'].lower()
    else:
      plot = 'full'

    url = API_URL % (Prefs['api_key'], metadata.id, plot)

    try:
      movie = JSON.ObjectFromURL(url, sleep=5.0)
    except:
      Log('*** Failed when trying to open url: %s ***' % (url))
      return None

    if 'Response' in movie and movie['Response'] == 'True':

      # Title
      if Prefs['use_title'] and 'Title' in movie:
        metadata.title = movie['Title']
      else:
        metadata.title = None

      # Year
      if Prefs['use_year'] and 'Year' in movie:
        metadata.year = int(movie['Year'])
      else:
        metadata.year = None

      # Plot
      if Prefs['use_plot'] and 'Plot' in movie and movie['Plot'] != 'N/A':
        metadata.summary = movie['Plot']
      else:
        metadata.summary = None

      # Content rating
      if Prefs['use_content_rating'] and 'Rated' in movie and movie['Rated'] != 'N/A':
        metadata.content_rating = movie['Rated']
      else:
        metadata.content_rating = None

      # Release date
      if Prefs['use_release_date'] and 'Released' in movie and movie['Released'] != 'N/A':
        metadata.originally_available_at = Datetime.ParseDate(movie['Released']).date()
      else:
        metadata.originally_available_at = None

      # Genres
      metadata.genres.clear()

      if Prefs['use_genres'] and 'Genre' in movie and movie['Genre'] != 'N/A':
        for genre in movie['Genre'].split(','):
          metadata.genres.add(genre.strip())

      # Production company
      if Prefs['use_production'] and 'Production' in movie and movie['Production'] != 'N/A':
        metadata.studio = movie['Production']
      else:
        metadata.studio = None

      # Directors
      metadata.directors.clear()

      if Prefs['use_directors'] and 'Director' in movie and movie['Director'] != 'N/A':
        for director in movie['Director'].split(','):
          try:
            meta_director = metadata.directors.new()
            meta_director.name = director.rsplit('(', 1)[0].strip()
          except:
            try:
              metadata.directors.add(director.rsplit('(', 1)[0].strip())
            except:
              pass

      # Writers
      metadata.writers.clear()

      if Prefs['use_writers'] and 'Writer' in movie and movie['Writer'] != 'N/A':
        for writer in movie['Writer'].split(','):
          try:
            meta_writer = metadata.writers.new()
            meta_writer.name = writer.rsplit('(', 1)[0].strip()
          except:
            try:
              metadata.writers.add(writer.rsplit('(', 1)[0].strip())
            except:
              pass

      # Actors
      metadata.roles.clear()

      if Prefs['use_actors'] and 'Actors' in movie and movie['Actors'] != 'N/A':
        for actor in movie['Actors'].split(','):
          role = metadata.roles.new()
          try:
            role.name = actor.strip()
          except:
            try:
              role.actor = actor.strip()
            except:
              pass

      # Runtime
      if Prefs['use_runtime'] and 'Runtime' in movie:
        duration = 0

        try:
          runtime = RE_RUNTIME.search(movie['Runtime']).groups()
          if 'hours' in runtime:
            duration += int(runtime['hours']) * 60 * 60 * 1000
          if 'minutes' in runtime:
            duration += int(runtime['minutes']) * 60 * 1000
        except:
          pass

        if duration > 0:
          metadata.duration = duration
        else:
          metadata.duration = None

      else:
        metadata.duration = None

      # Poster
      valid_names = list()

      if Prefs['use_poster'] and 'Poster' in movie and movie['Poster'] != 'N/A':

        fullsize = '%s@._V1.jpg' % (movie['Poster'].split('@', 1)[0])
        thumb = '%s@._V1._SX300.jpg' % (movie['Poster'].split('@', 1)[0])

        valid_names.append(fullsize)

        if fullsize not in metadata.posters:

          preview = HTTP.Request(thumb).content
          metadata.posters[fullsize] = Proxy.Preview(preview)

      metadata.posters.validate_keys(valid_names)

      # Rating
      if Prefs['use_rating']:

        rating_imdb = None
        rating_rt = None

        if 'imdbRating' in movie and movie['imdbRating'] != 'N/A':
          rating_imdb = movie['imdbRating']

        if 'tomatoMeter' in movie and movie['tomatoMeter'] != 'N/A':
          rating_rt = movie['tomatoMeter']

        if Prefs['rating'] == 'IMDb' and rating_imdb:
          metadata.rating = float(rating_imdb)
        elif Prefs['rating'] == 'Rotten Tomatoes' and rating_rt:
          metadata.rating = float(int(rating_rt)/10)

        if metadata.summary:
          summary = [metadata.summary]
        else:
          summary = []

        if Prefs['add_rating_rt'] and rating_rt:
          summary.append('Rotten Tomatoes: %s%%' % (rating_rt))

        if Prefs['add_rating_imdb'] and rating_imdb:
          summary.append('IMDb: %s' % (rating_imdb))

        if len(summary) > 0:
          summary.reverse()
          metadata.summary = '  ★  '.join(summary)

      else:
        metadata.rating = None

    else:
      Log('*** Failed when processing data from url: %s ***' % (url))
      return None
