// webpack.config.js
const { withExpo } = require('@expo/webpack-config');

module.exports = function (env, argv) {
  return withExpo(env, argv);
};
