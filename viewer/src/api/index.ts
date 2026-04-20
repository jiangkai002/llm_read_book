/** Generate by swagger-axios-codegen */
// @ts-nocheck
/* eslint-disable */

/** Generate by swagger-axios-codegen */
/* eslint-disable */
// @ts-nocheck
import axiosStatic from 'axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

export interface IRequestOptions extends AxiosRequestConfig {
  /**
   * show loading status
   */
  loading?: boolean;
  /**
   * display error message
   */
  showError?: boolean;
  /**
   * indicates whether Authorization credentials are required for the request
   * @default true
   */
  withAuthorization?: boolean;
}

export interface IRequestConfig {
  method?: any;
  headers?: any;
  url?: any;
  data?: any;
  params?: any;
}

// Add options interface
export interface ServiceOptions {
  axios?: AxiosInstance;
  /** only in axios interceptor config*/
  loading: boolean;
  showError: boolean;
}

// Add default options
export const serviceOptions: ServiceOptions = {};

// Instance selector
export function axios(configs: IRequestConfig, resolve: (p: any) => void, reject: (p: any) => void): Promise<any> {
  if (serviceOptions.axios) {
    return serviceOptions.axios
      .request(configs)
      .then((res) => {
        resolve(res.data);
      })
      .catch((err) => {
        reject(err);
      });
  } else {
    throw new Error('please inject yourself instance like axios  ');
  }
}

export function getConfigs(method: string, contentType: string, url: string, options: any): IRequestConfig {
  const configs: IRequestConfig = {
    loading: serviceOptions.loading,
    showError: serviceOptions.showError,
    ...options,
    method,
    url
  };
  configs.headers = {
    ...options.headers,
    'Content-Type': contentType
  };
  return configs;
}

export const basePath = '';

export interface IList<T> extends Array<T> {}
export interface List<T> extends Array<T> {}
export interface IDictionary<TValue> {
  [key: string]: TValue;
}
export interface Dictionary<TValue> extends IDictionary<TValue> {}

export interface IListResult<T> {
  items?: T[];
}

export class ListResultDto<T> implements IListResult<T> {
  items?: T[];
}

export interface IPagedResult<T> extends IListResult<T> {
  totalCount?: number;
  items?: T[];
}

export class PagedResultDto<T = any> implements IPagedResult<T> {
  totalCount?: number;
  items?: T[];
}

// customer definition
// empty

export class AuthService {
  /**
   * 用户登录
   */
  static loginApiAuthLoginPost(
    params: {
      /** requestBody */
      body?: Body_login_api_auth_login_post;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/auth/login';

      const configs: IRequestConfig = getConfigs('post', 'application/x-www-form-urlencoded', url, options);

      let data = params.body;

      configs.data = data;

      axios(configs, resolve, reject);
    });
  }
}

export class LlmService {
  /**
   * 读书场景多模态问答
   */
  static llmAskApiLlmLlmAskPost(
    params: {
      /** requestBody */
      body?: LLMAsk;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/llm/llm_ask';

      const configs: IRequestConfig = getConfigs('post', 'application/json', url, options);

      let data = params.body;

      configs.data = data;

      axios(configs, resolve, reject);
    });
  }
}

export class OneNoteService {
  /**
   * Onenote Auth Status
   */
  static onenoteAuthStatusApiOnenoteAuthStatusGet(options: IRequestOptions = {}): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/auth/status';

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Auth Logout
   */
  static onenoteAuthLogoutApiOnenoteAuthLogoutPost(options: IRequestOptions = {}): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/auth/logout';

      const configs: IRequestConfig = getConfigs('post', 'application/json', url, options);

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Auth Callback
   */
  static onenoteAuthCallbackApiOnenoteAuthCallbackGet(
    params: {
      /**  */
      code?: string;
      /**  */
      state?: string;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/auth/callback';

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);
      configs.params = { code: params['code'], state: params['state'] };

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Notebooks
   */
  static onenoteNotebooksApiOnenoteNotebooksGet(options: IRequestOptions = {}): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/notebooks';

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Sections
   */
  static onenoteSectionsApiOnenoteSectionsGet(
    params: {
      /**  */
      notebookId: string;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/sections';

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);
      configs.params = { notebook_id: params['notebookId'] };

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Pages
   */
  static onenotePagesApiOnenotePagesGet(
    params: {
      /**  */
      sectionId: string;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/pages';

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);
      configs.params = { section_id: params['sectionId'] };

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Create Page
   */
  static onenoteCreatePageApiOnenotePagesPost(
    params: {
      /** requestBody */
      body?: OneNoteCreatePageRequest;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/pages';

      const configs: IRequestConfig = getConfigs('post', 'application/json', url, options);

      let data = params.body;

      configs.data = data;

      axios(configs, resolve, reject);
    });
  }
  /**
   * Onenote Page Content
   */
  static onenotePageContentApiOnenotePagesPageIdContentGet(
    params: {
      /**  */
      pageId: string;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/onenote/pages/{page_id}/content';
      url = url.replace('{page_id}', params['pageId'] + '');

      const configs: IRequestConfig = getConfigs('get', 'application/json', url, options);

      axios(configs, resolve, reject);
    });
  }
}

export class GenerateNoteService {
  /**
   * 生成笔记
   */
  static generateNoteApiGenerateNoteGenerateNotePost(
    params: {
      /** requestBody */
      body?: GenerateNote;
    } = {} as any,
    options: IRequestOptions = {}
  ): Promise<any | null> {
    return new Promise((resolve, reject) => {
      let url = basePath + '/api/generate_note/generate_note';

      const configs: IRequestConfig = getConfigs('post', 'application/json', url, options);

      let data = params.body;

      configs.data = data;

      axios(configs, resolve, reject);
    });
  }
}

/** Body_login_api_auth_login_post */
export class Body_login_api_auth_login_post {
  /**  */
  'grant_type'?: any | null;

  /**  */
  'username': string;

  /**  */
  'password': string;

  /**  */
  'scope'?: string;

  /**  */
  'client_id'?: any | null;

  /**  */
  'client_secret'?: any | null;

  constructor(data: Body_login_api_auth_login_post = {}) {
    Object.assign(this, data);
  }
}

/** GenerateNote */
export class GenerateNote {
  /**  */
  'book_name': string;

  /**  */
  'question': string;

  /**  */
  'history_chat_list': string[];

  /**  */
  'api_key': string;

  /**  */
  'base_url': string;

  /**  */
  'model': string;

  /**  */
  'images': string[];

  constructor(data: GenerateNote = {}) {
    Object.assign(this, data);
  }
}

/** HTTPValidationError */
export class HTTPValidationError {
  /**  */
  'detail'?: ValidationError[];

  constructor(data: HTTPValidationError = {}) {
    Object.assign(this, data);
  }
}

/** LLMAsk */
export class LLMAsk {
  /** 当前阅读的书籍名称 */
  'book_name': string;

  /** 用户提出的问题 */
  'question': string;

  /** 页面截图的 PNG Base64 编码（不含 data:image 前缀） */
  'image_base64': string;

  /** 截图对应的文字内容或 OCR 结果，辅助模型理解 */
  'image_content': string;

  /** OpenAI 兼容 API 的密钥 */
  'api_key': string;

  /** API 根地址，例如 https:\/\/api.openai.com\/v1 */
  'base_url': string;

  /** 是否使用图片理解 */
  'use_image': boolean;

  /** 模型名称，可选支持 vision \/ 多模态 */
  'model': string;

  constructor(data: LLMAsk = {}) {
    Object.assign(this, data);
  }
}

/** OneNoteCreatePageRequest */
export class OneNoteCreatePageRequest {
  /**  */
  'section_id': string;

  /**  */
  'title': string;

  /**  */
  'html_content': string;

  constructor(data: OneNoteCreatePageRequest = {}) {
    Object.assign(this, data);
  }
}

/** ValidationError */
export class ValidationError {
  /**  */
  'loc': any | null[];

  /**  */
  'msg': string;

  /**  */
  'type': string;

  /**  */
  'input'?: any | null;

  /**  */
  'ctx'?: object;

  constructor(data: ValidationError = {}) {
    Object.assign(this, data);
  }
}
