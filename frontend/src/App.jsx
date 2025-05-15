import React, { useEffect, useState, useRef } from 'react';
import { RefreshCw, Search, Edit, Check, XCircle, ChevronLeft, RotateCcw, Upload, Image } from 'lucide-react';

function App() {
  const [flacs, setFlacs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [viewType, setViewType] = useState('grid');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('default');
  const [showExtrasMenu, setShowExtrasMenu] = useState(false);
  const [showExtras, setShowExtras] = useState({ genre: false, tracknumber: true, date: false });
  const [editMode, setEditMode] = useState({});
  const [markedFields, setMarkedFields] = useState({});
  const [editedValues, setEditedValues] = useState({});
  const [searchMode, setSearchMode] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const vantaRef = useRef(null);
  const [coverSearchMode, setCoverSearchMode] = useState(false);	
  const [coverSearchResults, setCoverSearchResults] = useState({
    musicbrainz: [],
    web: []
  });
  const [coverSearchLoading, setCoverSearchLoading] = useState(false);
  const fileInputRef = useRef(null);


  // Función para entrar en modo de búsqueda de carátulas
  const enterCoverSearchMode = () => {
    if (!selected) return;
    
    setCoverSearchMode(true);
    setCoverSearchResults({
      musicbrainz: [],
      web: []
    });
    setCoverSearchLoading(true);
    
    // Buscar carátulas en MusicBrainz usando el artista y álbum seleccionados
    searchCoversMusicBrainz(selected.artist, selected.album);
    
    // Buscar carátulas en la web
    searchCoversWeb(selected.artist, selected.album);
  };

  // Función para buscar portadas en MusicBrainz
  const searchCoversMusicBrainz = async (artist, album) => {
    const userAgent = "EchoMiniNormalizer/1.0 ( your-email@example.com )";
    
    try {
      // Primero buscar el álbum en MusicBrainz
      const searchUrl = `https://musicbrainz.org/ws/2/release?query=${encodeURIComponent(`artist:${artist} AND release:${album}`)}&fmt=json&limit=5`;
      const response = await fetch(searchUrl, {
        headers: {
          'User-Agent': userAgent,
          'Accept': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`MusicBrainz API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Extraer los IDs de release para buscar portadas
      const releaseIds = data.releases.map(release => release.id);
      
      // Para cada release, buscar su portada en CoverArtArchive
      const coverPromises = releaseIds.map(async (id) => {
        try {
          const coverUrl = `https://coverartarchive.org/release/${id}`;
          const coverResponse = await fetch(coverUrl, {
            headers: { 'User-Agent': userAgent }
          });
          
          if (!coverResponse.ok) return null;
          
          const coverData = await coverResponse.json();
          
          // Retornar solo la URL de la imagen frontal
          const frontImage = coverData.images.find(img => img.front) || coverData.images[0];
          return frontImage ? {
            url: frontImage.image,
            thumbnailUrl: frontImage.thumbnails.small,
            source: 'MusicBrainz',
            id: id
          } : null;
        } catch (error) {
          return null;
        }
      });
      
      // Esperar a que todas las búsquedas de imágenes se completen y filtrar los nulos
      const covers = (await Promise.all(coverPromises)).filter(cover => cover !== null);
      
      setCoverSearchResults(prev => ({
        ...prev,
        musicbrainz: covers
      }));
    } catch (error) {
      console.error("Error searching covers in MusicBrainz:", error);
    } finally {
      setCoverSearchLoading(false);
    }
  };

  // Función para buscar portadas en la web (usando una API alternativa como Deezer)
  const searchCoversWeb = async (artist, album) => {
    try {
      // Usamos la API de Deezer como alternativa a Google Images
      const searchUrl = `https://api.deezer.com/search?q=${encodeURIComponent(`${artist} ${album}`)}&limit=5`;
      
      const response = await fetch(searchUrl);
      if (!response.ok) {
        throw new Error(`Deezer API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Extraer las portadas de los álbumes encontrados (evitando duplicados)
      const covers = data.data
        .filter((item, index, self) => 
          index === self.findIndex(t => t.album.cover_big === item.album.cover_big)
        )
        .map(item => ({
          url: item.album.cover_big,
          thumbnailUrl: item.album.cover_medium,
          source: 'Deezer',
          id: item.album.id
        }));
      
      setCoverSearchResults(prev => ({
        ...prev,
        web: covers
      }));
    } catch (error) {
      console.error("Error searching covers on the web:", error);
    } finally {
      setCoverSearchLoading(false);
    }
  };

  // Función para salir del modo de búsqueda de carátulas
  const exitCoverSearchMode = () => {
    setCoverSearchMode(false);
    setCoverSearchResults({
      musicbrainz: [],
      web: []
    });
  };

  // Función para aplicar una carátula seleccionada
  const applySelectedCover = async (coverUrl) => {
    try {
      // Descargar la imagen
      const response = await fetch(coverUrl);
      const blob = await response.blob();
      
      // Preparar FormData para enviar al servidor
      const formData = new FormData();
      formData.append('cover', blob, 'cover.jpg');
      
      // Enviar al backend
      const updateResponse = await fetch(
        `http://localhost:8000/api/cover/${encodeURIComponent(selected.filename)}`,
        {
          method: 'PUT',
          body: formData
        }
      );
      
      if (!updateResponse.ok) {
        throw new Error('Error al guardar la carátula');
      }
      
      // Actualizar la interfaz
      exitCoverSearchMode();
      
      // Forzar recarga de la imagen actualizando el timestamp
      const timestamp = new Date().getTime();
      const coverImg = document.querySelector(`.cover-image-${selected.filename}`);
      if (coverImg) {
        coverImg.src = `http://localhost:8000/api/cover/${encodeURIComponent(selected.filename)}?t=${timestamp}`;
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  // Función para manejar la subida de archivos
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    
    const formData = new FormData();
    formData.append('cover', file);
    
    fetch(`http://localhost:8000/api/cover/${encodeURIComponent(selected.filename)}`, {
      method: 'PUT',
      body: formData
    })
    .then(response => {
      if (!response.ok) throw new Error('Error al subir la carátula');
      return response.json();
    })
    .then(() => {
      exitCoverSearchMode();
      // Forzar recarga de la imagen
      const timestamp = new Date().getTime();
      const coverImg = document.querySelector(`.cover-image-${selected.filename}`);
      if (coverImg) {
        coverImg.src = `http://localhost:8000/api/cover/${encodeURIComponent(selected.filename)}?t=${timestamp}`;
      }
    })
    .catch(error => {
      console.error('Error:', error);
    });
  };
  // First create a function to handle track selection
const selectTrack = (track) => {
  // Reset marked fields when changing tracks
  setMarkedFields({});
  
  // Exit any edit mode that might be active
  setEditMode({});
  
  // Clear any edited values
  setEditedValues({});
  
  // Set the selected track
  setSelected(track);
};

  // Fondo Vanta.js fijo
  useEffect(() => {
    if (window.VANTA) {
      const effect = window.VANTA.NET({
        el: vantaRef.current,
        backgroundColor: 0x0b1e40,
        color: 0x1da1f2,
        maxDistance: 30.0,
        spacing: 25.0,
        mouseControls: false,
        touchControls: false,
        gyroControls: false
      });
      return () => effect.destroy();
    }
  }, []);

  // Carga FLACs
  useEffect(() => {
    fetch('http://localhost:8000/api/flacs')
      .then(r => r.json())
      .then(setFlacs)
      .catch(console.error);
  }, []);

  // Toggle edit mode for a field
  const toggleEdit = (field) => {
    setEditMode(prev => {
      const newState = { ...prev };
      newState[field] = !prev[field];
      return newState;
    });
    
    // Initialize edited value when entering edit mode
    if (!editMode[field] && selected) {
      setEditedValues(prev => ({
        ...prev,
        [field]: selected[field] || ''
      }));
    }
  };

  // Toggle mark for a field
  const toggleMark = (field) => {
    setMarkedFields(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  // Handle editing field value
  const handleEdit = (field, value) => {
    setEditedValues(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Function to get genre information for a selected result
const fetchGenreInfo = async (mbid) => {
  const userAgent = "EchoMiniNormalizer/1.0 ( your-email@example.com )";
  
  try {
    // Get recording details with genre tags
    const url = `https://musicbrainz.org/ws/2/recording/${mbid}?inc=genres&fmt=json`;
    const response = await fetch(url, {
      headers: {
        'User-Agent': userAgent,
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`MusicBrainz API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Extract genre from tags
    let genre = '';
    if (data.genres && data.genres.length > 0) {
      // Sort genres by count and take the highest
      const sortedGenres = [...data.genres].sort((a, b) => b.count - a.count);
      genre = sortedGenres[0].name;
    }
    
    return genre;
  } catch (error) {
    console.error("Error fetching genre info:", error);
    return '';
  }
};



// Function to search MusicBrainz API
const searchMusicBrainz = async (query) => {
  // MusicBrainz requires a user-agent
  const userAgent = "EchoMiniNormalizer/1.0 ( your-email@example.com )";
  
  try {
    // First search for recordings matching the query
    const searchUrl = `https://musicbrainz.org/ws/2/recording?query=${encodeURIComponent(query)}&fmt=json&limit=10`;
    const response = await fetch(searchUrl, {
      headers: {
        'User-Agent': userAgent,
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`MusicBrainz API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Transform the results to match our application's format
    const results = data.recordings.map(recording => {
      // Extract artist from artist-credit
      const artist = recording['artist-credit']?.map(credit => credit.name || credit.artist?.name).join('') || '';
      
      // Extract album from the first release
      const album = recording.releases?.[0]?.title || '';
      const date = recording.releases?.[0]?.year?.split('-')[0] || '';
      const tracknumber = recording.releases?.[0]?.['track-count'] || '';
      
      return {
        id: recording.id,
        title: recording.title || '',
        artist: artist,
        album: album,
        date: date,
        tracknumber: tracknumber,
        genre: '' // MusicBrainz doesn't return genre in basic recording search
      };
    });
    
    return results;
  } catch (error) {
    console.error("Error searching MusicBrainz:", error);
    return [];
  }
};


// Save edited field
const saveField = (field) => {
  if (selected && editedValues[field] !== undefined) {
    // Prepare the update object - only include the field being updated
    const updateData = {
      [field]: editedValues[field]
    };
    
    // Send PUT request to backend
    fetch(`http://localhost:8000/api/flacs/${encodeURIComponent(selected.filename)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData),
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Error al guardar los cambios');
      }
      return response.json();
    })
    .then(updatedData => {
      // update local state with server response
      setSelected(updatedData);
      setEditedValues(prev => {
        const newValues = {...prev};
        delete newValues[field];
        return newValues;
      });
      toggleEdit(field);
    })
    .catch(error => {
      console.error('Error:', error);
      // Aquí podrías mostrar un mensaje de error al usuario
    });
  }
};

  // Cancel editing
  const cancelEdit = (field) => {
    toggleEdit(field);
  };

// Modified enterSearchMode function
const enterSearchMode = () => {
  setSearchMode(true);
  setSearchResults([]); // Clear previous results
  
  // Prepare search query based on selected track
  if (selected) {
    const query = `${selected.artist} ${selected.title}`;
    setSearchTerm(query);
    
    // Show loading state
    setSearchResults([]);
    
    // Perform actual search
    searchMusicBrainz(query).then(results => {
      if (results.length > 0) {
        setSearchResults(results);
      } else {
        // If no results, try a broader search
        searchMusicBrainz(selected.artist).then(artistResults => {
          setSearchResults(artistResults);
        });
      }
    });
  }
};

  // Exit search mode
  const exitSearchMode = () => {
    setSearchMode(false);
    setSearchResults([]);
  };

// Modified applySelectedResult function
const applySelectedResult = async (result) => {
  if (selected) {
    // If we're missing genre and it's marked, try to fetch it
    if (markedFields.genre && !result.genre && result.id) {
      const genre = await fetchGenreInfo(result.id);
      if (genre) {
        result.genre = genre;
      }
    }
    
    const updatedTrack = { ...selected };
    
    // update only marked fields
    Object.keys(markedFields).forEach(field => {
      if (markedFields[field] && result[field]) {
        updatedTrack[field] = result[field];
      }
    });
    
    setSelected(updatedTrack);
    exitSearchMode();
    
    // If we want to save the changes to the backend, we can do it here
    // Similar to what's done in saveField()
  }
};
// Add this to your component to handle manual search
const handleManualSearch = () => {
  if (searchTerm.trim()) {
    searchMusicBrainz(searchTerm).then(results => {
      setSearchResults(results);
    });
  }
};
  // Metadatos más comunes para editar
  const commonMetadata = [
    { key: 'title', label: 'Título' },
    { key: 'artist', label: 'Artista' },
    { key: 'album', label: 'Álbum' },
    { key: 'tracknumber', label: 'Pista #' },
    { key: 'genre', label: 'Género' },
    { key: 'date', label: 'Año' }
  ];

  // Metadatos adicionales
  const additionalMetadata = [
    { key: 'year', label: 'Fecha' },
    { key: 'discnumber', label: 'Disco #' },
    { key: 'totaldiscs', label: 'Total discos' },
    { key: 'lyrics', label: 'Letra' }
  ];

  // Filtrado
  const filtered = flacs.filter(f => {
    const term = searchTerm.toLowerCase();
    return (
      f.filename?.toLowerCase().includes(term) ||
      f.title?.toLowerCase().includes(term) ||
      f.artist?.toLowerCase().includes(term) ||
      f.album?.toLowerCase().includes(term)
    );
  });

  // Ordenado
  const sorted = [...filtered].sort((a, b) => {
    switch (sortBy) {
      case 'album':    return (a.album || '').localeCompare(b.album || '');
      case 'artist':   return (a.artist || '').localeCompare(b.artist || '');
      case 'title':    return (a.title || '').localeCompare(b.title || '');
      case 'date':     return (a.date || '').localeCompare(b.date || '');
      case 'genre':    return (a.genre || '').localeCompare(b.genre || '');
      default:         return 0;
    }
  });

  // Renderizar un campo de metadatos editable
  const renderMetadataField = (field, label) => {
    if (!selected) return null;
    
    return (
      <div className="flex items-center justify-between mb-2 group">
        <div className="flex-1">
          <strong>{label}:</strong> 
          {editMode[field] ? (
            <input
              type="text"
              value={editedValues[field] || ''}
              onChange={(e) => handleEdit(field, e.target.value)}
              className="ml-2 px-2 py-1 border rounded w-full"
            />
          ) : (
            <span className="ml-2">{selected[field] || '—'}</span>
          )}
        </div>
        <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {editMode[field] ? (
            <>
              <button 
                onClick={() => saveField(field)}
                className="p-1 text-green-600 hover:text-green-800"
                title="Guardar"
              >
                <Check size={16} />
              </button>
              <button 
                onClick={() => cancelEdit(field)}
                className="p-1 text-red-600 hover:text-red-800"
                title="Cancelar"
              >
                <XCircle size={16} />
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={() => toggleEdit(field)}
                className="p-1 text-blue-600 hover:text-blue-800"
                title="Editar"
              >
                <Edit size={16} />
              </button>
              <button 
                onClick={() => toggleMark(field)}
                className={`p-1 ${markedFields[field] ? 'text-purple-600' : 'text-gray-400'} hover:text-purple-800`}
                title={markedFields[field] ? "Marcado" : "Marcar"}
              >
                {markedFields[field] ? "✓" : "☐"}
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Fondo animado */}
      <div ref={vantaRef} className="fixed inset-0 z-0" />

      {/* Contenedor principal */}
      <div className="relative z-10 flex h-screen w-full flex-col p-4 space-y-4 overflow-visible">

        {/* Header con nuevas opciones */}
        <header className="relative z-20 flex items-center justify-between p-4 bg-white/20 backdrop-blur rounded-t-lg overflow-visible">
          <div className="flex items-center space-x-4">
            {/* Buscador */}
            <input
              type="text"
              placeholder="Buscar..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring"
            />

            {/* Ordenar */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="px-3 py-2 rounded-md border border-gray-300 bg-white focus:outline-none focus:ring"
            >
              <option value="default">Ordenar</option>
              <option value="album">Por Álbum</option>
              <option value="artist">Por Artista</option>
              <option value="title">Por Título</option>
              <option value="date">Por Año</option>
              <option value="genre">Por Género</option>
            </select>

            {/* Mostrar extras (solo en lista) */}
            {viewType === 'list' && (
              <div className="relative">
                <button
                  onClick={() => setShowExtrasMenu(v => !v)}
                  className="px-3 py-2 rounded-md border border-gray-300 bg-white focus:outline-none focus:ring"
                >
                  Mostrar extras
                </button>
                {showExtrasMenu && (
                  <div className="absolute mt-2 p-3 bg-white rounded-lg shadow-lg z-50">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={showExtras.genre}
                        onChange={() => setShowExtras(e => ({ ...e, genre: !e.genre }))}
                      />
                      <span>Género</span>
                    </label>
                    <label className="flex items-center space-x-2 mt-1">
                      <input
                        type="checkbox"
                        checked={showExtras.tracknumber}
                        onChange={() => setShowExtras(e => ({ ...e, tracknumber: !e.tracknumber }))}
                      />
                      <span># de Pista</span>
                    </label>
                    <label className="flex items-center space-x-2 mt-1">
                      <input
                        type="checkbox"
                        checked={showExtras.date}
                        onChange={() => setShowExtras(e => ({ ...e, date: !e.date }))}
                      />
                      <span>Año</span>
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Toggle Grid/Lista */}
          <button
            onClick={() => setViewType(v => v === 'grid' ? 'list' : 'grid')}
            className="ml-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {viewType === 'grid' ? 'Ver Lista' : 'Ver Grid'}
          </button>
        </header>

        {/* Cuerpo con espacio entre main y sidebar */}
        <div className="flex flex-1 gap-4 min-h-0">

          {/* Main scrollable */}
          <main className="flex-1 overflow-auto p-4 bg-white/20 backdrop-blur rounded-lg min-h-0">
            {viewType === 'grid' ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6">
                {sorted.map(f => (
                  <div
                    key={f.filename}
                    onClick={() => selectTrack(f)}
                    className={`cursor-pointer rounded-lg overflow-hidden shadow-lg transform hover:scale-105 transition ${selected?.filename === f.filename ? 'ring-4 ring-blue-300' : ''}`}
                  >
                    <div className="w-full" style={{ paddingBottom: '100%', position: 'relative' }}>
                      <img
                        src={`http://localhost:8000/api/cover/${encodeURIComponent(f.filename)}`}
                        alt="Portada"
                        className="absolute inset-0 w-full h-full object-cover"
                      />
                    </div>
                    <div className="p-3 bg-white">
                      <h2 className="font-semibold text-gray-800 truncate">{f.title || f.filename}</h2>
                      <p className="text-sm text-gray-600">{f.artist}</p>
                      <p className="text-sm text-gray-600 italic">{f.album}</p>
                      <p className="text-xs text-gray-500">#{f.tracknumber}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <ul className="space-y-2">
                {sorted.map(f => (
                  <li
                    key={f.filename}
                    onClick={() => selectTrack(f)}
                    className={`cursor-pointer p-3 bg-white rounded-lg shadow hover:bg-gray-100 transition flex items-center ${selected?.filename === f.filename ? 'bg-blue-100' : ''}`}
                  >
                    <img
                      src={`http://localhost:8000/api/cover/${encodeURIComponent(f.filename)}`}
                      alt="Portada"
                      className="w-12 h-12 object-cover rounded mr-4 flex-shrink-0"
                    />
                    <div className="flex-1">
                      <div className="flex justify-between">
                        <span>{f.title || f.filename}</span>
                        {showExtras.tracknumber && <span className="text-gray-500">#{f.tracknumber}</span>}
                      </div>
                      <div className="text-sm text-gray-600">{f.artist} — {f.album}</div>
                      {showExtras.genre && <div className="text-sm text-gray-600">Género: {f.genre || '—'}</div>}
                      {showExtras.date && <div className="text-sm text-gray-600">Año: {f.date || '—'}</div>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </main>

          {/* Sidebar metadatos scrollable */}
      <aside className="w-1/3 h-full overflow-auto bg-white/80 p-4 backdrop-blur rounded-lg min-h-0">
        {selected ? (
          <>
            {/* Control buttons */}
            <div className="flex justify-between mb-4">
              {coverSearchMode ? (
                <>
                  <button 
                    onClick={exitCoverSearchMode}
                    className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    <ChevronLeft size={16} />
                    <span>Volver</span>
                  </button>
                </>
              ) : searchMode ? (
                    <>
                      <button 
                        onClick={exitSearchMode}
                        className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        <ChevronLeft size={16} />
                        <span>Volver</span>
                      </button>
                      <button 
                        onClick={() => {
                          if (searchResults.length > 0) {
                            applySelectedResult(searchResults[0]);
                          }
                        }}
                        className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                        disabled={searchResults.length === 0}
                      >
                        <RotateCcw size={16} />
                        <span>Reemplazar</span>
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={() => {
                          // Refresh metadata from server
                          if (selected) {
                            fetch(`http://localhost:8000/api/flacs/${encodeURIComponent(selected.filename)}`)
                              .then(r => r.json())
                              .then(data => {
                                setSelected(data);
                                setEditedValues({});
                              })
                              .catch(console.error);
                          }
                        }}
                        className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        <RefreshCw size={16} />
                        <span>Actualizar</span>
                      </button>
                      <button 
                        onClick={enterSearchMode}
                        className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        <Search size={16} />
                        <span>Buscar</span>
                      </button>
                    </>
                  )}
                </div>

                {coverSearchMode ? (
              // Modo de búsqueda de carátulas
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Buscar Carátula</h3>
                
                {/* Opción de subir archivo */}
                <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded text-center">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="image/*"
                  />
                  <button 
                    onClick={() => fileInputRef.current.click()}
                    className="flex items-center justify-center space-x-2 mx-auto px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    <Upload size={16} />
                    <span>Subir Imagen</span>
                  </button>
                </div>
                
                {/* Resultados MusicBrainz */}
                <div>
                  <h4 className="font-medium mb-2">MusicBrainz</h4>
                  {coverSearchLoading && coverSearchResults.musicbrainz.length === 0 ? (
                    <p className="text-center text-gray-500">Buscando...</p>
                  ) : coverSearchResults.musicbrainz.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {coverSearchResults.musicbrainz.map(cover => (
                        <div 
                          key={cover.id}
                          className="cursor-pointer border rounded overflow-hidden hover:shadow-lg transition"
                          onClick={() => applySelectedCover(cover.url)}
                        >
                          <img 
                            src={cover.thumbnailUrl || cover.url} 
                            alt="Portada" 
                            className="w-full h-32 object-cover"
                          />
                          <div className="p-2 text-xs text-center">MusicBrainz</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500">No se encontraron resultados</p>
                  )}
                </div>
                
                {/* Resultados Web */}
                <div>
                  <h4 className="font-medium mb-2">Búsqueda Web</h4>
                  {coverSearchLoading && coverSearchResults.web.length === 0 ? (
                    <p className="text-center text-gray-500">Buscando...</p>
                  ) : coverSearchResults.web.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {coverSearchResults.web.map(cover => (
                        <div 
                          key={cover.id}
                          className="cursor-pointer border rounded overflow-hidden hover:shadow-lg transition"
                          onClick={() => applySelectedCover(cover.url)}
                        >
                          <img 
                            src={cover.thumbnailUrl || cover.url} 
                            alt="Portada" 
                            className="w-full h-32 object-cover"
                          />
                          <div className="p-2 text-xs text-center">{cover.source}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500">No se encontraron resultados</p>
                  )}
                </div>
              </div>
            ) : searchMode ? (
                  // Search mode display
                  <div className="space-y-4">
                    					<div>
					  <input
						type="text"
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="w-full px-3 py-2 border rounded"
						placeholder="Buscar en MusicBrainz..."
						onKeyPress={(e) => e.key === 'Enter' && handleManualSearch()}
					  />
					  <button
						onClick={handleManualSearch}
						className="mt-2 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
					  >
						Buscar
					  </button>
					</div>
                    
                    <div className="text-sm text-gray-600 mb-2">
                      Resultados de búsqueda en MusicBrainz:
                    </div>
                    
                    {searchResults.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        Buscando resultados...
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {searchResults.map(result => (
                          <div 
                            key={result.id}
                            className="p-3 border rounded bg-white hover:bg-blue-50 cursor-pointer"
                            onClick={() => applySelectedResult(result)}
                            title="Haz clic para aplicar este resultado a los campos marcados"
                          >
                            <h4 className="font-semibold">{result.title}</h4>
                            <p>{result.artist} — {result.album} ({result.date})</p>
                            <p className="text-sm text-gray-600">
                              Pista #{result.tracknumber} • {result.genre}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  // Normal metadata display
                  <>
                    {/* Cover art - smaller size */}
                    {/* Cover art - clickeable para buscar carátulas */}
<div 
  className="mx-auto mb-4 cursor-pointer relative group" 
  style={{ width: '70%', paddingBottom: '70%', position: 'relative' }}
  onClick={enterCoverSearchMode}
>
  <img
    src={`http://localhost:8000/api/cover/${encodeURIComponent(selected.filename)}`}
    alt="Portada"
    className={`absolute inset-0 w-full h-full object-cover rounded cover-image-${selected.filename}`}
  />
  <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity rounded">
    <div className="text-white flex flex-col items-center">
      <Image size={32} />
      <span className="mt-2">Cambiar carátula</span>
    </div>
  </div>
</div>
                    
                    {/* Title shown larger */}
                    <h3 className="text-xl font-bold mb-4 truncate">{selected.title || selected.filename}</h3>
                    
                    {/* Common metadata fields with edit/mark buttons */}
                    <div className="mb-6 space-y-1">
                      {commonMetadata.map(meta => renderMetadataField(meta.key, meta.label))}
                    </div>
                    
                    {/* Technical details */}
                    <div className="mb-4">
                      <h4 className="font-semibold mb-2 text-gray-700">Detalles técnicos</h4>
                      <p className="text-sm"><strong>Archivo:</strong> {selected.filename}</p>
                      <p className="text-sm"><strong>Duración:</strong> {Math.floor(selected.length / 60)}:{(selected.length % 60).toString().padStart(2, '0')}</p>
                      <p className="text-sm"><strong>Tasa de bits:</strong> {Math.round(selected.bitrate / 1000)} kbps</p>
                    </div>
                    
                    {/* Additional metadata (collapsible) */}
                    <details className="mb-4">
                      <summary className="font-semibold text-gray-700 cursor-pointer">Metadatos adicionales</summary>
                      <div className="pl-2 mt-2 space-y-1">
                        {additionalMetadata.map(meta => renderMetadataField(meta.key, meta.label))}
                      </div>
                    </details>
                  </>
                )}
              </>
            ) : (
              <p className="text-center text-gray-500">Selecciona una pista para ver detalles.</p>
            )}
          </aside>
        </div>
      </div>
    </>
  );
}

export default App;