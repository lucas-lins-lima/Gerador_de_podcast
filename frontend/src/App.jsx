// frontend/src/App.jsx
import React from 'react';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-800 to-indigo-900 text-white flex items-center justify-center p-4">
      <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-xl shadow-2xl p-8 md:p-12 text-center max-w-md w-full border border-purple-500">
        <h1 className="text-4xl md:text-5xl font-extrabold mb-6 text-purple-200 drop-shadow-lg">
          🎙️ Gerador de Podcast
        </h1>
        <p className="text-lg md:text-xl mb-8 text-purple-100">
          Transforme seus PDFs em podcasts envolventes com a ajuda da IA!
        </p>
        <button
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 ease-in-out transform hover:scale-105 shadow-lg"
          onClick={() => alert('Botão de upload clicado! (Funcionalidade em breve)')}
        >
          Carregar PDF
        </button>
      </div>
    </div>
  );
}

export default App;
