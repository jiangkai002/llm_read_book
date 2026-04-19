const { codegen } = require('swagger-axios-codegen')
const axios = require('axios')

axios.get('http://localhost:8000/openapi.json').then((resp) => {
  codegen({
    source: resp.data,
    useStaticMethod: true,
    outputDir: './src/api',
    fileName: 'index.ts',
    modelMode: 'class',
    disableTypeCheck: false, // 启用类型检查，允许 IDE 跳转
  })
})
