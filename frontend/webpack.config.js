const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');
require('dotenv').config();

module.exports = {
  entry: {
    content: './src/content.js',
    popup: './src/popup.js',
    background: './src/background.js'
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env']
          }
        }
      }
    ]
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: 'src/manifest.json', to: 'manifest.json' },
        { from: 'src/popup.html', to: 'popup.html' },
        { from: 'src/config.js', to: 'config.js', 
          transform(content) {
            // Convert Buffer to string, replace the hardcoded API key with the environment variable
            const contentStr = content.toString();
            const apiKey = process.env.GEMINI_API_KEY || 'YOUR_GEMINI_API_KEY';
            const replaced = contentStr.replace(
              /GEMINI_API_KEY: 'AIzaSyA0n-1Q7OzY9yXFOF7SUNuy_2nK8UQvgIY'/g, 
              `GEMINI_API_KEY: '${apiKey}'`
            );
            return Buffer.from(replaced);
          }
        }
      ]
    }),
    new webpack.DefinePlugin({
      'process.env.GEMINI_API_KEY': JSON.stringify(process.env.GEMINI_API_KEY)
    })
  ],
  resolve: {
    fallback: {
      "crypto": require.resolve("crypto-browserify"),
      "stream": require.resolve("stream-browserify"),
      "buffer": require.resolve("buffer"),
      "util": require.resolve("util/"),
      "url": require.resolve("url/"),
      "querystring": require.resolve("querystring-es3"),
      "path": require.resolve("path-browserify"),
      "fs": false,
      "net": false,
      "tls": false
    }
  },
  optimization: {
    splitChunks: {
      chunks: (chunk) => chunk.name !== 'background',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: (chunk) => chunk.name !== 'background',
        }
      }
    }
  }
}; 