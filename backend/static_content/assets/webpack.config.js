const path = require('path');
const webpack = require('webpack');
const TerserPlugin = require('terser-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebPackPlugin = require('html-webpack-plugin');
const {CleanWebpackPlugin} = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');
module.exports = (env, argv) => {
    return {
        mode: argv.mode,
        entry: "./index.js",
        output: {
            path: path.resolve(__dirname, 'dist'),
            filename: '[name].js',
        },

        module: {

            rules: [
                {
                    test: /\.(sass|scss|css)$/,
                    use: [{
                        loader: argv.mode !== 'production' ? 'style-loader' : MiniCssExtractPlugin.loader, // inject CSS to page
                    }, {
                        loader: 'css-loader', // translates CSS into CommonJS modules
                    }, {
                        loader: 'postcss-loader', // Run post css actions
                        options: {
                            postcssOptions: {
                                plugins: function () { // post css plugins, can be exported to postcss.config.js
                                    return [
                                        require('precss'),
                                        require('autoprefixer')
                                    ];
                                }
                            }
                        }
                    }, {
                        loader: 'sass-loader' // compiles Sass to CSS
                    }]

                },
                {
                    test: /\.html$/,
                    loader: 'html-loader',
                    options: {
                        minimize: true,
                        removeComments: true,
                        collapseWhitespace: true,
                    },
                },


                {
                    test: /\.(svg|eot|woff|woff2|ttf)$/,
                    use: ['file-loader']
                }


            ]


        },
        plugins: [

            new webpack.ProvidePlugin({
                $: 'jquery',
                jQuery: 'jquery',
                'window.$': 'jquery',
                'window.jQuery': 'jquery',
                Waves: 'node-waves',
                _: 'underscore',
                Promise: 'es6-promise',
            }),
            new webpack.ProvidePlugin({
                process: 'process/browser',
            }),
            new MiniCssExtractPlugin({
                filename: argv.mode !== 'production' ? '[name].css' : '[name].[hash].css',
                chunkFilename: argv.mode !== 'production' ? '[id].css' : '[id].[hash].css',

            }),

            new CleanWebpackPlugin(),
        ],


    }
}