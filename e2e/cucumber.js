module.exports = {
  default: {
    paths: [
      'features/**/*.feature'
    ],
    require: [
      'steps/**/*.ts',
      'test_setup.ts'
    ],
    requireModule: [
      'ts-node/register'
    ],
    format: [
      '@serenity-js/cucumber'
    ],
    formatOptions: {
      specDirectory: 'features'
    }
  }
}
