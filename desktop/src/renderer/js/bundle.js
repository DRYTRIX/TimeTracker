(() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __esm = (fn, res) => function __init() {
    return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
  };
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // node_modules/axios/dist/browser/axios.cjs
  var require_axios = __commonJS({
    "node_modules/axios/dist/browser/axios.cjs"(exports, module) {
      "use strict";
      function bind(fn, thisArg) {
        return function wrap2() {
          return fn.apply(thisArg, arguments);
        };
      }
      var { toString: toString2 } = Object.prototype;
      var { getPrototypeOf } = Object;
      var { iterator, toStringTag: toStringTag2 } = Symbol;
      var kindOf = /* @__PURE__ */ ((cache) => (thing) => {
        const str = toString2.call(thing);
        return cache[str] || (cache[str] = str.slice(8, -1).toLowerCase());
      })(/* @__PURE__ */ Object.create(null));
      var kindOfTest = (type2) => {
        type2 = type2.toLowerCase();
        return (thing) => kindOf(thing) === type2;
      };
      var typeOfTest = (type2) => (thing) => typeof thing === type2;
      var { isArray: isArray2 } = Array;
      var isUndefined = typeOfTest("undefined");
      function isBuffer(val) {
        return val !== null && !isUndefined(val) && val.constructor !== null && !isUndefined(val.constructor) && isFunction$1(val.constructor.isBuffer) && val.constructor.isBuffer(val);
      }
      var isArrayBuffer = kindOfTest("ArrayBuffer");
      function isArrayBufferView(val) {
        let result;
        if (typeof ArrayBuffer !== "undefined" && ArrayBuffer.isView) {
          result = ArrayBuffer.isView(val);
        } else {
          result = val && val.buffer && isArrayBuffer(val.buffer);
        }
        return result;
      }
      var isString = typeOfTest("string");
      var isFunction$1 = typeOfTest("function");
      var isNumber = typeOfTest("number");
      var isObject = (thing) => thing !== null && typeof thing === "object";
      var isBoolean = (thing) => thing === true || thing === false;
      var isPlainObject = (val) => {
        if (kindOf(val) !== "object") {
          return false;
        }
        const prototype2 = getPrototypeOf(val);
        return (prototype2 === null || prototype2 === Object.prototype || Object.getPrototypeOf(prototype2) === null) && !(toStringTag2 in val) && !(iterator in val);
      };
      var isEmptyObject = (val) => {
        if (!isObject(val) || isBuffer(val)) {
          return false;
        }
        try {
          return Object.keys(val).length === 0 && Object.getPrototypeOf(val) === Object.prototype;
        } catch (e) {
          return false;
        }
      };
      var isDate = kindOfTest("Date");
      var isFile = kindOfTest("File");
      var isBlob = kindOfTest("Blob");
      var isFileList = kindOfTest("FileList");
      var isStream = (val) => isObject(val) && isFunction$1(val.pipe);
      var isFormData = (thing) => {
        let kind;
        return thing && (typeof FormData === "function" && thing instanceof FormData || isFunction$1(thing.append) && ((kind = kindOf(thing)) === "formdata" || // detect form-data instance
        kind === "object" && isFunction$1(thing.toString) && thing.toString() === "[object FormData]"));
      };
      var isURLSearchParams = kindOfTest("URLSearchParams");
      var [isReadableStream, isRequest, isResponse, isHeaders] = ["ReadableStream", "Request", "Response", "Headers"].map(kindOfTest);
      var trim = (str) => str.trim ? str.trim() : str.replace(/^[\s\uFEFF\xA0]+|[\s\uFEFF\xA0]+$/g, "");
      function forEach(obj, fn, { allOwnKeys = false } = {}) {
        if (obj === null || typeof obj === "undefined") {
          return;
        }
        let i;
        let l;
        if (typeof obj !== "object") {
          obj = [obj];
        }
        if (isArray2(obj)) {
          for (i = 0, l = obj.length; i < l; i++) {
            fn.call(null, obj[i], i, obj);
          }
        } else {
          if (isBuffer(obj)) {
            return;
          }
          const keys2 = allOwnKeys ? Object.getOwnPropertyNames(obj) : Object.keys(obj);
          const len = keys2.length;
          let key;
          for (i = 0; i < len; i++) {
            key = keys2[i];
            fn.call(null, obj[key], key, obj);
          }
        }
      }
      function findKey(obj, key) {
        if (isBuffer(obj)) {
          return null;
        }
        key = key.toLowerCase();
        const keys2 = Object.keys(obj);
        let i = keys2.length;
        let _key;
        while (i-- > 0) {
          _key = keys2[i];
          if (key === _key.toLowerCase()) {
            return _key;
          }
        }
        return null;
      }
      var _global2 = (() => {
        if (typeof globalThis !== "undefined") return globalThis;
        return typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : global;
      })();
      var isContextDefined = (context) => !isUndefined(context) && context !== _global2;
      function merge() {
        const { caseless, skipUndefined } = isContextDefined(this) && this || {};
        const result = {};
        const assignValue = (val, key) => {
          const targetKey = caseless && findKey(result, key) || key;
          if (isPlainObject(result[targetKey]) && isPlainObject(val)) {
            result[targetKey] = merge(result[targetKey], val);
          } else if (isPlainObject(val)) {
            result[targetKey] = merge({}, val);
          } else if (isArray2(val)) {
            result[targetKey] = val.slice();
          } else if (!skipUndefined || !isUndefined(val)) {
            result[targetKey] = val;
          }
        };
        for (let i = 0, l = arguments.length; i < l; i++) {
          arguments[i] && forEach(arguments[i], assignValue);
        }
        return result;
      }
      var extend2 = (a, b, thisArg, { allOwnKeys } = {}) => {
        forEach(b, (val, key) => {
          if (thisArg && isFunction$1(val)) {
            a[key] = bind(val, thisArg);
          } else {
            a[key] = val;
          }
        }, { allOwnKeys });
        return a;
      };
      var stripBOM = (content) => {
        if (content.charCodeAt(0) === 65279) {
          content = content.slice(1);
        }
        return content;
      };
      var inherits = (constructor, superConstructor, props2, descriptors2) => {
        constructor.prototype = Object.create(superConstructor.prototype, descriptors2);
        constructor.prototype.constructor = constructor;
        Object.defineProperty(constructor, "super", {
          value: superConstructor.prototype
        });
        props2 && Object.assign(constructor.prototype, props2);
      };
      var toFlatObject = (sourceObj, destObj, filter, propFilter) => {
        let props2;
        let i;
        let prop;
        const merged = {};
        destObj = destObj || {};
        if (sourceObj == null) return destObj;
        do {
          props2 = Object.getOwnPropertyNames(sourceObj);
          i = props2.length;
          while (i-- > 0) {
            prop = props2[i];
            if ((!propFilter || propFilter(prop, sourceObj, destObj)) && !merged[prop]) {
              destObj[prop] = sourceObj[prop];
              merged[prop] = true;
            }
          }
          sourceObj = filter !== false && getPrototypeOf(sourceObj);
        } while (sourceObj && (!filter || filter(sourceObj, destObj)) && sourceObj !== Object.prototype);
        return destObj;
      };
      var endsWith = (str, searchString, position) => {
        str = String(str);
        if (position === void 0 || position > str.length) {
          position = str.length;
        }
        position -= searchString.length;
        const lastIndex = str.indexOf(searchString, position);
        return lastIndex !== -1 && lastIndex === position;
      };
      var toArray = (thing) => {
        if (!thing) return null;
        if (isArray2(thing)) return thing;
        let i = thing.length;
        if (!isNumber(i)) return null;
        const arr = new Array(i);
        while (i-- > 0) {
          arr[i] = thing[i];
        }
        return arr;
      };
      var isTypedArray = /* @__PURE__ */ ((TypedArray) => {
        return (thing) => {
          return TypedArray && thing instanceof TypedArray;
        };
      })(typeof Uint8Array !== "undefined" && getPrototypeOf(Uint8Array));
      var forEachEntry = (obj, fn) => {
        const generator = obj && obj[iterator];
        const _iterator = generator.call(obj);
        let result;
        while ((result = _iterator.next()) && !result.done) {
          const pair = result.value;
          fn.call(obj, pair[0], pair[1]);
        }
      };
      var matchAll = (regExp, str) => {
        let matches;
        const arr = [];
        while ((matches = regExp.exec(str)) !== null) {
          arr.push(matches);
        }
        return arr;
      };
      var isHTMLForm = kindOfTest("HTMLFormElement");
      var toCamelCase = (str) => {
        return str.toLowerCase().replace(
          /[-_\s]([a-z\d])(\w*)/g,
          function replacer(m, p1, p2) {
            return p1.toUpperCase() + p2;
          }
        );
      };
      var hasOwnProperty = (({ hasOwnProperty: hasOwnProperty2 }) => (obj, prop) => hasOwnProperty2.call(obj, prop))(Object.prototype);
      var isRegExp = kindOfTest("RegExp");
      var reduceDescriptors = (obj, reducer) => {
        const descriptors2 = Object.getOwnPropertyDescriptors(obj);
        const reducedDescriptors = {};
        forEach(descriptors2, (descriptor, name) => {
          let ret;
          if ((ret = reducer(descriptor, name, obj)) !== false) {
            reducedDescriptors[name] = ret || descriptor;
          }
        });
        Object.defineProperties(obj, reducedDescriptors);
      };
      var freezeMethods = (obj) => {
        reduceDescriptors(obj, (descriptor, name) => {
          if (isFunction$1(obj) && ["arguments", "caller", "callee"].indexOf(name) !== -1) {
            return false;
          }
          const value = obj[name];
          if (!isFunction$1(value)) return;
          descriptor.enumerable = false;
          if ("writable" in descriptor) {
            descriptor.writable = false;
            return;
          }
          if (!descriptor.set) {
            descriptor.set = () => {
              throw Error("Can not rewrite read-only method '" + name + "'");
            };
          }
        });
      };
      var toObjectSet = (arrayOrString, delimiter) => {
        const obj = {};
        const define = (arr) => {
          arr.forEach((value) => {
            obj[value] = true;
          });
        };
        isArray2(arrayOrString) ? define(arrayOrString) : define(String(arrayOrString).split(delimiter));
        return obj;
      };
      var noop = () => {
      };
      var toFiniteNumber = (value, defaultValue) => {
        return value != null && Number.isFinite(value = +value) ? value : defaultValue;
      };
      function isSpecCompliantForm(thing) {
        return !!(thing && isFunction$1(thing.append) && thing[toStringTag2] === "FormData" && thing[iterator]);
      }
      var toJSONObject = (obj) => {
        const stack = new Array(10);
        const visit = (source, i) => {
          if (isObject(source)) {
            if (stack.indexOf(source) >= 0) {
              return;
            }
            if (isBuffer(source)) {
              return source;
            }
            if (!("toJSON" in source)) {
              stack[i] = source;
              const target = isArray2(source) ? [] : {};
              forEach(source, (value, key) => {
                const reducedValue = visit(value, i + 1);
                !isUndefined(reducedValue) && (target[key] = reducedValue);
              });
              stack[i] = void 0;
              return target;
            }
          }
          return source;
        };
        return visit(obj, 0);
      };
      var isAsyncFn = kindOfTest("AsyncFunction");
      var isThenable = (thing) => thing && (isObject(thing) || isFunction$1(thing)) && isFunction$1(thing.then) && isFunction$1(thing.catch);
      var _setImmediate = ((setImmediateSupported, postMessageSupported) => {
        if (setImmediateSupported) {
          return setImmediate;
        }
        return postMessageSupported ? ((token, callbacks) => {
          _global2.addEventListener("message", ({ source, data }) => {
            if (source === _global2 && data === token) {
              callbacks.length && callbacks.shift()();
            }
          }, false);
          return (cb) => {
            callbacks.push(cb);
            _global2.postMessage(token, "*");
          };
        })(`axios@${Math.random()}`, []) : (cb) => setTimeout(cb);
      })(
        typeof setImmediate === "function",
        isFunction$1(_global2.postMessage)
      );
      var asap2 = typeof queueMicrotask !== "undefined" ? queueMicrotask.bind(_global2) : typeof process !== "undefined" && process.nextTick || _setImmediate;
      var isIterable = (thing) => thing != null && isFunction$1(thing[iterator]);
      var utils$1 = {
        isArray: isArray2,
        isArrayBuffer,
        isBuffer,
        isFormData,
        isArrayBufferView,
        isString,
        isNumber,
        isBoolean,
        isObject,
        isPlainObject,
        isEmptyObject,
        isReadableStream,
        isRequest,
        isResponse,
        isHeaders,
        isUndefined,
        isDate,
        isFile,
        isBlob,
        isRegExp,
        isFunction: isFunction$1,
        isStream,
        isURLSearchParams,
        isTypedArray,
        isFileList,
        forEach,
        merge,
        extend: extend2,
        trim,
        stripBOM,
        inherits,
        toFlatObject,
        kindOf,
        kindOfTest,
        endsWith,
        toArray,
        forEachEntry,
        matchAll,
        isHTMLForm,
        hasOwnProperty,
        hasOwnProp: hasOwnProperty,
        // an alias to avoid ESLint no-prototype-builtins detection
        reduceDescriptors,
        freezeMethods,
        toObjectSet,
        toCamelCase,
        noop,
        toFiniteNumber,
        findKey,
        global: _global2,
        isContextDefined,
        isSpecCompliantForm,
        toJSONObject,
        isAsyncFn,
        isThenable,
        setImmediate: _setImmediate,
        asap: asap2,
        isIterable
      };
      function AxiosError(message, code, config, request, response) {
        Error.call(this);
        if (Error.captureStackTrace) {
          Error.captureStackTrace(this, this.constructor);
        } else {
          this.stack = new Error().stack;
        }
        this.message = message;
        this.name = "AxiosError";
        code && (this.code = code);
        config && (this.config = config);
        request && (this.request = request);
        if (response) {
          this.response = response;
          this.status = response.status ? response.status : null;
        }
      }
      utils$1.inherits(AxiosError, Error, {
        toJSON: function toJSON() {
          return {
            // Standard
            message: this.message,
            name: this.name,
            // Microsoft
            description: this.description,
            number: this.number,
            // Mozilla
            fileName: this.fileName,
            lineNumber: this.lineNumber,
            columnNumber: this.columnNumber,
            stack: this.stack,
            // Axios
            config: utils$1.toJSONObject(this.config),
            code: this.code,
            status: this.status
          };
        }
      });
      var prototype$1 = AxiosError.prototype;
      var descriptors = {};
      [
        "ERR_BAD_OPTION_VALUE",
        "ERR_BAD_OPTION",
        "ECONNABORTED",
        "ETIMEDOUT",
        "ERR_NETWORK",
        "ERR_FR_TOO_MANY_REDIRECTS",
        "ERR_DEPRECATED",
        "ERR_BAD_RESPONSE",
        "ERR_BAD_REQUEST",
        "ERR_CANCELED",
        "ERR_NOT_SUPPORT",
        "ERR_INVALID_URL"
        // eslint-disable-next-line func-names
      ].forEach((code) => {
        descriptors[code] = { value: code };
      });
      Object.defineProperties(AxiosError, descriptors);
      Object.defineProperty(prototype$1, "isAxiosError", { value: true });
      AxiosError.from = (error, code, config, request, response, customProps) => {
        const axiosError = Object.create(prototype$1);
        utils$1.toFlatObject(error, axiosError, function filter(obj) {
          return obj !== Error.prototype;
        }, (prop) => {
          return prop !== "isAxiosError";
        });
        const msg = error && error.message ? error.message : "Error";
        const errCode = code == null && error ? error.code : code;
        AxiosError.call(axiosError, msg, errCode, config, request, response);
        if (error && axiosError.cause == null) {
          Object.defineProperty(axiosError, "cause", { value: error, configurable: true });
        }
        axiosError.name = error && error.name || "Error";
        customProps && Object.assign(axiosError, customProps);
        return axiosError;
      };
      var httpAdapter = null;
      function isVisitable(thing) {
        return utils$1.isPlainObject(thing) || utils$1.isArray(thing);
      }
      function removeBrackets(key) {
        return utils$1.endsWith(key, "[]") ? key.slice(0, -2) : key;
      }
      function renderKey(path, key, dots) {
        if (!path) return key;
        return path.concat(key).map(function each(token, i) {
          token = removeBrackets(token);
          return !dots && i ? "[" + token + "]" : token;
        }).join(dots ? "." : "");
      }
      function isFlatArray(arr) {
        return utils$1.isArray(arr) && !arr.some(isVisitable);
      }
      var predicates = utils$1.toFlatObject(utils$1, {}, null, function filter(prop) {
        return /^is[A-Z]/.test(prop);
      });
      function toFormData(obj, formData, options) {
        if (!utils$1.isObject(obj)) {
          throw new TypeError("target must be an object");
        }
        formData = formData || new FormData();
        options = utils$1.toFlatObject(options, {
          metaTokens: true,
          dots: false,
          indexes: false
        }, false, function defined(option, source) {
          return !utils$1.isUndefined(source[option]);
        });
        const metaTokens = options.metaTokens;
        const visitor = options.visitor || defaultVisitor;
        const dots = options.dots;
        const indexes = options.indexes;
        const _Blob = options.Blob || typeof Blob !== "undefined" && Blob;
        const useBlob = _Blob && utils$1.isSpecCompliantForm(formData);
        if (!utils$1.isFunction(visitor)) {
          throw new TypeError("visitor must be a function");
        }
        function convertValue(value) {
          if (value === null) return "";
          if (utils$1.isDate(value)) {
            return value.toISOString();
          }
          if (utils$1.isBoolean(value)) {
            return value.toString();
          }
          if (!useBlob && utils$1.isBlob(value)) {
            throw new AxiosError("Blob is not supported. Use a Buffer instead.");
          }
          if (utils$1.isArrayBuffer(value) || utils$1.isTypedArray(value)) {
            return useBlob && typeof Blob === "function" ? new Blob([value]) : Buffer.from(value);
          }
          return value;
        }
        function defaultVisitor(value, key, path) {
          let arr = value;
          if (value && !path && typeof value === "object") {
            if (utils$1.endsWith(key, "{}")) {
              key = metaTokens ? key : key.slice(0, -2);
              value = JSON.stringify(value);
            } else if (utils$1.isArray(value) && isFlatArray(value) || (utils$1.isFileList(value) || utils$1.endsWith(key, "[]")) && (arr = utils$1.toArray(value))) {
              key = removeBrackets(key);
              arr.forEach(function each(el, index) {
                !(utils$1.isUndefined(el) || el === null) && formData.append(
                  // eslint-disable-next-line no-nested-ternary
                  indexes === true ? renderKey([key], index, dots) : indexes === null ? key : key + "[]",
                  convertValue(el)
                );
              });
              return false;
            }
          }
          if (isVisitable(value)) {
            return true;
          }
          formData.append(renderKey(path, key, dots), convertValue(value));
          return false;
        }
        const stack = [];
        const exposedHelpers = Object.assign(predicates, {
          defaultVisitor,
          convertValue,
          isVisitable
        });
        function build(value, path) {
          if (utils$1.isUndefined(value)) return;
          if (stack.indexOf(value) !== -1) {
            throw Error("Circular reference detected in " + path.join("."));
          }
          stack.push(value);
          utils$1.forEach(value, function each(el, key) {
            const result = !(utils$1.isUndefined(el) || el === null) && visitor.call(
              formData,
              el,
              utils$1.isString(key) ? key.trim() : key,
              path,
              exposedHelpers
            );
            if (result === true) {
              build(el, path ? path.concat(key) : [key]);
            }
          });
          stack.pop();
        }
        if (!utils$1.isObject(obj)) {
          throw new TypeError("data must be an object");
        }
        build(obj);
        return formData;
      }
      function encode$1(str) {
        const charMap = {
          "!": "%21",
          "'": "%27",
          "(": "%28",
          ")": "%29",
          "~": "%7E",
          "%20": "+",
          "%00": "\0"
        };
        return encodeURIComponent(str).replace(/[!'()~]|%20|%00/g, function replacer(match) {
          return charMap[match];
        });
      }
      function AxiosURLSearchParams(params, options) {
        this._pairs = [];
        params && toFormData(params, this, options);
      }
      var prototype = AxiosURLSearchParams.prototype;
      prototype.append = function append(name, value) {
        this._pairs.push([name, value]);
      };
      prototype.toString = function toString3(encoder) {
        const _encode = encoder ? function(value) {
          return encoder.call(this, value, encode$1);
        } : encode$1;
        return this._pairs.map(function each(pair) {
          return _encode(pair[0]) + "=" + _encode(pair[1]);
        }, "").join("&");
      };
      function encode(val) {
        return encodeURIComponent(val).replace(/%3A/gi, ":").replace(/%24/g, "$").replace(/%2C/gi, ",").replace(/%20/g, "+");
      }
      function buildURL(url, params, options) {
        if (!params) {
          return url;
        }
        const _encode = options && options.encode || encode;
        if (utils$1.isFunction(options)) {
          options = {
            serialize: options
          };
        }
        const serializeFn = options && options.serialize;
        let serializedParams;
        if (serializeFn) {
          serializedParams = serializeFn(params, options);
        } else {
          serializedParams = utils$1.isURLSearchParams(params) ? params.toString() : new AxiosURLSearchParams(params, options).toString(_encode);
        }
        if (serializedParams) {
          const hashmarkIndex = url.indexOf("#");
          if (hashmarkIndex !== -1) {
            url = url.slice(0, hashmarkIndex);
          }
          url += (url.indexOf("?") === -1 ? "?" : "&") + serializedParams;
        }
        return url;
      }
      var InterceptorManager = class {
        constructor() {
          this.handlers = [];
        }
        /**
         * Add a new interceptor to the stack
         *
         * @param {Function} fulfilled The function to handle `then` for a `Promise`
         * @param {Function} rejected The function to handle `reject` for a `Promise`
         *
         * @return {Number} An ID used to remove interceptor later
         */
        use(fulfilled, rejected, options) {
          this.handlers.push({
            fulfilled,
            rejected,
            synchronous: options ? options.synchronous : false,
            runWhen: options ? options.runWhen : null
          });
          return this.handlers.length - 1;
        }
        /**
         * Remove an interceptor from the stack
         *
         * @param {Number} id The ID that was returned by `use`
         *
         * @returns {void}
         */
        eject(id) {
          if (this.handlers[id]) {
            this.handlers[id] = null;
          }
        }
        /**
         * Clear all interceptors from the stack
         *
         * @returns {void}
         */
        clear() {
          if (this.handlers) {
            this.handlers = [];
          }
        }
        /**
         * Iterate over all the registered interceptors
         *
         * This method is particularly useful for skipping over any
         * interceptors that may have become `null` calling `eject`.
         *
         * @param {Function} fn The function to call for each interceptor
         *
         * @returns {void}
         */
        forEach(fn) {
          utils$1.forEach(this.handlers, function forEachHandler(h) {
            if (h !== null) {
              fn(h);
            }
          });
        }
      };
      var InterceptorManager$1 = InterceptorManager;
      var transitionalDefaults = {
        silentJSONParsing: true,
        forcedJSONParsing: true,
        clarifyTimeoutError: false
      };
      var URLSearchParams$1 = typeof URLSearchParams !== "undefined" ? URLSearchParams : AxiosURLSearchParams;
      var FormData$1 = typeof FormData !== "undefined" ? FormData : null;
      var Blob$1 = typeof Blob !== "undefined" ? Blob : null;
      var platform$1 = {
        isBrowser: true,
        classes: {
          URLSearchParams: URLSearchParams$1,
          FormData: FormData$1,
          Blob: Blob$1
        },
        protocols: ["http", "https", "file", "blob", "url", "data"]
      };
      var hasBrowserEnv = typeof window !== "undefined" && typeof document !== "undefined";
      var _navigator = typeof navigator === "object" && navigator || void 0;
      var hasStandardBrowserEnv = hasBrowserEnv && (!_navigator || ["ReactNative", "NativeScript", "NS"].indexOf(_navigator.product) < 0);
      var hasStandardBrowserWebWorkerEnv = (() => {
        return typeof WorkerGlobalScope !== "undefined" && // eslint-disable-next-line no-undef
        self instanceof WorkerGlobalScope && typeof self.importScripts === "function";
      })();
      var origin = hasBrowserEnv && window.location.href || "http://localhost";
      var utils = /* @__PURE__ */ Object.freeze({
        __proto__: null,
        hasBrowserEnv,
        hasStandardBrowserWebWorkerEnv,
        hasStandardBrowserEnv,
        navigator: _navigator,
        origin
      });
      var platform = {
        ...utils,
        ...platform$1
      };
      function toURLEncodedForm(data, options) {
        return toFormData(data, new platform.classes.URLSearchParams(), {
          visitor: function(value, key, path, helpers) {
            if (platform.isNode && utils$1.isBuffer(value)) {
              this.append(key, value.toString("base64"));
              return false;
            }
            return helpers.defaultVisitor.apply(this, arguments);
          },
          ...options
        });
      }
      function parsePropPath(name) {
        return utils$1.matchAll(/\w+|\[(\w*)]/g, name).map((match) => {
          return match[0] === "[]" ? "" : match[1] || match[0];
        });
      }
      function arrayToObject2(arr) {
        const obj = {};
        const keys2 = Object.keys(arr);
        let i;
        const len = keys2.length;
        let key;
        for (i = 0; i < len; i++) {
          key = keys2[i];
          obj[key] = arr[key];
        }
        return obj;
      }
      function formDataToJSON(formData) {
        function buildPath(path, value, target, index) {
          let name = path[index++];
          if (name === "__proto__") return true;
          const isNumericKey = Number.isFinite(+name);
          const isLast = index >= path.length;
          name = !name && utils$1.isArray(target) ? target.length : name;
          if (isLast) {
            if (utils$1.hasOwnProp(target, name)) {
              target[name] = [target[name], value];
            } else {
              target[name] = value;
            }
            return !isNumericKey;
          }
          if (!target[name] || !utils$1.isObject(target[name])) {
            target[name] = [];
          }
          const result = buildPath(path, value, target[name], index);
          if (result && utils$1.isArray(target[name])) {
            target[name] = arrayToObject2(target[name]);
          }
          return !isNumericKey;
        }
        if (utils$1.isFormData(formData) && utils$1.isFunction(formData.entries)) {
          const obj = {};
          utils$1.forEachEntry(formData, (name, value) => {
            buildPath(parsePropPath(name), value, obj, 0);
          });
          return obj;
        }
        return null;
      }
      function stringifySafely(rawValue, parser, encoder) {
        if (utils$1.isString(rawValue)) {
          try {
            (parser || JSON.parse)(rawValue);
            return utils$1.trim(rawValue);
          } catch (e) {
            if (e.name !== "SyntaxError") {
              throw e;
            }
          }
        }
        return (encoder || JSON.stringify)(rawValue);
      }
      var defaults = {
        transitional: transitionalDefaults,
        adapter: ["xhr", "http", "fetch"],
        transformRequest: [function transformRequest(data, headers) {
          const contentType = headers.getContentType() || "";
          const hasJSONContentType = contentType.indexOf("application/json") > -1;
          const isObjectPayload = utils$1.isObject(data);
          if (isObjectPayload && utils$1.isHTMLForm(data)) {
            data = new FormData(data);
          }
          const isFormData2 = utils$1.isFormData(data);
          if (isFormData2) {
            return hasJSONContentType ? JSON.stringify(formDataToJSON(data)) : data;
          }
          if (utils$1.isArrayBuffer(data) || utils$1.isBuffer(data) || utils$1.isStream(data) || utils$1.isFile(data) || utils$1.isBlob(data) || utils$1.isReadableStream(data)) {
            return data;
          }
          if (utils$1.isArrayBufferView(data)) {
            return data.buffer;
          }
          if (utils$1.isURLSearchParams(data)) {
            headers.setContentType("application/x-www-form-urlencoded;charset=utf-8", false);
            return data.toString();
          }
          let isFileList2;
          if (isObjectPayload) {
            if (contentType.indexOf("application/x-www-form-urlencoded") > -1) {
              return toURLEncodedForm(data, this.formSerializer).toString();
            }
            if ((isFileList2 = utils$1.isFileList(data)) || contentType.indexOf("multipart/form-data") > -1) {
              const _FormData = this.env && this.env.FormData;
              return toFormData(
                isFileList2 ? { "files[]": data } : data,
                _FormData && new _FormData(),
                this.formSerializer
              );
            }
          }
          if (isObjectPayload || hasJSONContentType) {
            headers.setContentType("application/json", false);
            return stringifySafely(data);
          }
          return data;
        }],
        transformResponse: [function transformResponse(data) {
          const transitional = this.transitional || defaults.transitional;
          const forcedJSONParsing = transitional && transitional.forcedJSONParsing;
          const JSONRequested = this.responseType === "json";
          if (utils$1.isResponse(data) || utils$1.isReadableStream(data)) {
            return data;
          }
          if (data && utils$1.isString(data) && (forcedJSONParsing && !this.responseType || JSONRequested)) {
            const silentJSONParsing = transitional && transitional.silentJSONParsing;
            const strictJSONParsing = !silentJSONParsing && JSONRequested;
            try {
              return JSON.parse(data, this.parseReviver);
            } catch (e) {
              if (strictJSONParsing) {
                if (e.name === "SyntaxError") {
                  throw AxiosError.from(e, AxiosError.ERR_BAD_RESPONSE, this, null, this.response);
                }
                throw e;
              }
            }
          }
          return data;
        }],
        /**
         * A timeout in milliseconds to abort a request. If set to 0 (default) a
         * timeout is not created.
         */
        timeout: 0,
        xsrfCookieName: "XSRF-TOKEN",
        xsrfHeaderName: "X-XSRF-TOKEN",
        maxContentLength: -1,
        maxBodyLength: -1,
        env: {
          FormData: platform.classes.FormData,
          Blob: platform.classes.Blob
        },
        validateStatus: function validateStatus(status) {
          return status >= 200 && status < 300;
        },
        headers: {
          common: {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": void 0
          }
        }
      };
      utils$1.forEach(["delete", "get", "head", "post", "put", "patch"], (method) => {
        defaults.headers[method] = {};
      });
      var defaults$1 = defaults;
      var ignoreDuplicateOf = utils$1.toObjectSet([
        "age",
        "authorization",
        "content-length",
        "content-type",
        "etag",
        "expires",
        "from",
        "host",
        "if-modified-since",
        "if-unmodified-since",
        "last-modified",
        "location",
        "max-forwards",
        "proxy-authorization",
        "referer",
        "retry-after",
        "user-agent"
      ]);
      var parseHeaders = (rawHeaders) => {
        const parsed = {};
        let key;
        let val;
        let i;
        rawHeaders && rawHeaders.split("\n").forEach(function parser(line) {
          i = line.indexOf(":");
          key = line.substring(0, i).trim().toLowerCase();
          val = line.substring(i + 1).trim();
          if (!key || parsed[key] && ignoreDuplicateOf[key]) {
            return;
          }
          if (key === "set-cookie") {
            if (parsed[key]) {
              parsed[key].push(val);
            } else {
              parsed[key] = [val];
            }
          } else {
            parsed[key] = parsed[key] ? parsed[key] + ", " + val : val;
          }
        });
        return parsed;
      };
      var $internals = Symbol("internals");
      function normalizeHeader(header) {
        return header && String(header).trim().toLowerCase();
      }
      function normalizeValue(value) {
        if (value === false || value == null) {
          return value;
        }
        return utils$1.isArray(value) ? value.map(normalizeValue) : String(value);
      }
      function parseTokens(str) {
        const tokens = /* @__PURE__ */ Object.create(null);
        const tokensRE = /([^\s,;=]+)\s*(?:=\s*([^,;]+))?/g;
        let match;
        while (match = tokensRE.exec(str)) {
          tokens[match[1]] = match[2];
        }
        return tokens;
      }
      var isValidHeaderName = (str) => /^[-_a-zA-Z0-9^`|~,!#$%&'*+.]+$/.test(str.trim());
      function matchHeaderValue(context, value, header, filter, isHeaderNameFilter) {
        if (utils$1.isFunction(filter)) {
          return filter.call(this, value, header);
        }
        if (isHeaderNameFilter) {
          value = header;
        }
        if (!utils$1.isString(value)) return;
        if (utils$1.isString(filter)) {
          return value.indexOf(filter) !== -1;
        }
        if (utils$1.isRegExp(filter)) {
          return filter.test(value);
        }
      }
      function formatHeader(header) {
        return header.trim().toLowerCase().replace(/([a-z\d])(\w*)/g, (w, char, str) => {
          return char.toUpperCase() + str;
        });
      }
      function buildAccessors(obj, header) {
        const accessorName = utils$1.toCamelCase(" " + header);
        ["get", "set", "has"].forEach((methodName) => {
          Object.defineProperty(obj, methodName + accessorName, {
            value: function(arg1, arg2, arg3) {
              return this[methodName].call(this, header, arg1, arg2, arg3);
            },
            configurable: true
          });
        });
      }
      var AxiosHeaders = class {
        constructor(headers) {
          headers && this.set(headers);
        }
        set(header, valueOrRewrite, rewrite) {
          const self2 = this;
          function setHeader(_value, _header, _rewrite) {
            const lHeader = normalizeHeader(_header);
            if (!lHeader) {
              throw new Error("header name must be a non-empty string");
            }
            const key = utils$1.findKey(self2, lHeader);
            if (!key || self2[key] === void 0 || _rewrite === true || _rewrite === void 0 && self2[key] !== false) {
              self2[key || _header] = normalizeValue(_value);
            }
          }
          const setHeaders = (headers, _rewrite) => utils$1.forEach(headers, (_value, _header) => setHeader(_value, _header, _rewrite));
          if (utils$1.isPlainObject(header) || header instanceof this.constructor) {
            setHeaders(header, valueOrRewrite);
          } else if (utils$1.isString(header) && (header = header.trim()) && !isValidHeaderName(header)) {
            setHeaders(parseHeaders(header), valueOrRewrite);
          } else if (utils$1.isObject(header) && utils$1.isIterable(header)) {
            let obj = {}, dest, key;
            for (const entry of header) {
              if (!utils$1.isArray(entry)) {
                throw TypeError("Object iterator must return a key-value pair");
              }
              obj[key = entry[0]] = (dest = obj[key]) ? utils$1.isArray(dest) ? [...dest, entry[1]] : [dest, entry[1]] : entry[1];
            }
            setHeaders(obj, valueOrRewrite);
          } else {
            header != null && setHeader(valueOrRewrite, header, rewrite);
          }
          return this;
        }
        get(header, parser) {
          header = normalizeHeader(header);
          if (header) {
            const key = utils$1.findKey(this, header);
            if (key) {
              const value = this[key];
              if (!parser) {
                return value;
              }
              if (parser === true) {
                return parseTokens(value);
              }
              if (utils$1.isFunction(parser)) {
                return parser.call(this, value, key);
              }
              if (utils$1.isRegExp(parser)) {
                return parser.exec(value);
              }
              throw new TypeError("parser must be boolean|regexp|function");
            }
          }
        }
        has(header, matcher) {
          header = normalizeHeader(header);
          if (header) {
            const key = utils$1.findKey(this, header);
            return !!(key && this[key] !== void 0 && (!matcher || matchHeaderValue(this, this[key], key, matcher)));
          }
          return false;
        }
        delete(header, matcher) {
          const self2 = this;
          let deleted = false;
          function deleteHeader(_header) {
            _header = normalizeHeader(_header);
            if (_header) {
              const key = utils$1.findKey(self2, _header);
              if (key && (!matcher || matchHeaderValue(self2, self2[key], key, matcher))) {
                delete self2[key];
                deleted = true;
              }
            }
          }
          if (utils$1.isArray(header)) {
            header.forEach(deleteHeader);
          } else {
            deleteHeader(header);
          }
          return deleted;
        }
        clear(matcher) {
          const keys2 = Object.keys(this);
          let i = keys2.length;
          let deleted = false;
          while (i--) {
            const key = keys2[i];
            if (!matcher || matchHeaderValue(this, this[key], key, matcher, true)) {
              delete this[key];
              deleted = true;
            }
          }
          return deleted;
        }
        normalize(format) {
          const self2 = this;
          const headers = {};
          utils$1.forEach(this, (value, header) => {
            const key = utils$1.findKey(headers, header);
            if (key) {
              self2[key] = normalizeValue(value);
              delete self2[header];
              return;
            }
            const normalized = format ? formatHeader(header) : String(header).trim();
            if (normalized !== header) {
              delete self2[header];
            }
            self2[normalized] = normalizeValue(value);
            headers[normalized] = true;
          });
          return this;
        }
        concat(...targets) {
          return this.constructor.concat(this, ...targets);
        }
        toJSON(asStrings) {
          const obj = /* @__PURE__ */ Object.create(null);
          utils$1.forEach(this, (value, header) => {
            value != null && value !== false && (obj[header] = asStrings && utils$1.isArray(value) ? value.join(", ") : value);
          });
          return obj;
        }
        [Symbol.iterator]() {
          return Object.entries(this.toJSON())[Symbol.iterator]();
        }
        toString() {
          return Object.entries(this.toJSON()).map(([header, value]) => header + ": " + value).join("\n");
        }
        getSetCookie() {
          return this.get("set-cookie") || [];
        }
        get [Symbol.toStringTag]() {
          return "AxiosHeaders";
        }
        static from(thing) {
          return thing instanceof this ? thing : new this(thing);
        }
        static concat(first, ...targets) {
          const computed = new this(first);
          targets.forEach((target) => computed.set(target));
          return computed;
        }
        static accessor(header) {
          const internals = this[$internals] = this[$internals] = {
            accessors: {}
          };
          const accessors = internals.accessors;
          const prototype2 = this.prototype;
          function defineAccessor(_header) {
            const lHeader = normalizeHeader(_header);
            if (!accessors[lHeader]) {
              buildAccessors(prototype2, _header);
              accessors[lHeader] = true;
            }
          }
          utils$1.isArray(header) ? header.forEach(defineAccessor) : defineAccessor(header);
          return this;
        }
      };
      AxiosHeaders.accessor(["Content-Type", "Content-Length", "Accept", "Accept-Encoding", "User-Agent", "Authorization"]);
      utils$1.reduceDescriptors(AxiosHeaders.prototype, ({ value }, key) => {
        let mapped = key[0].toUpperCase() + key.slice(1);
        return {
          get: () => value,
          set(headerValue) {
            this[mapped] = headerValue;
          }
        };
      });
      utils$1.freezeMethods(AxiosHeaders);
      var AxiosHeaders$1 = AxiosHeaders;
      function transformData(fns, response) {
        const config = this || defaults$1;
        const context = response || config;
        const headers = AxiosHeaders$1.from(context.headers);
        let data = context.data;
        utils$1.forEach(fns, function transform(fn) {
          data = fn.call(config, data, headers.normalize(), response ? response.status : void 0);
        });
        headers.normalize();
        return data;
      }
      function isCancel(value) {
        return !!(value && value.__CANCEL__);
      }
      function CanceledError(message, config, request) {
        AxiosError.call(this, message == null ? "canceled" : message, AxiosError.ERR_CANCELED, config, request);
        this.name = "CanceledError";
      }
      utils$1.inherits(CanceledError, AxiosError, {
        __CANCEL__: true
      });
      function settle(resolve, reject, response) {
        const validateStatus = response.config.validateStatus;
        if (!response.status || !validateStatus || validateStatus(response.status)) {
          resolve(response);
        } else {
          reject(new AxiosError(
            "Request failed with status code " + response.status,
            [AxiosError.ERR_BAD_REQUEST, AxiosError.ERR_BAD_RESPONSE][Math.floor(response.status / 100) - 4],
            response.config,
            response.request,
            response
          ));
        }
      }
      function parseProtocol(url) {
        const match = /^([-+\w]{1,25})(:?\/\/|:)/.exec(url);
        return match && match[1] || "";
      }
      function speedometer(samplesCount, min) {
        samplesCount = samplesCount || 10;
        const bytes = new Array(samplesCount);
        const timestamps = new Array(samplesCount);
        let head = 0;
        let tail = 0;
        let firstSampleTS;
        min = min !== void 0 ? min : 1e3;
        return function push(chunkLength) {
          const now = Date.now();
          const startedAt = timestamps[tail];
          if (!firstSampleTS) {
            firstSampleTS = now;
          }
          bytes[head] = chunkLength;
          timestamps[head] = now;
          let i = tail;
          let bytesCount = 0;
          while (i !== head) {
            bytesCount += bytes[i++];
            i = i % samplesCount;
          }
          head = (head + 1) % samplesCount;
          if (head === tail) {
            tail = (tail + 1) % samplesCount;
          }
          if (now - firstSampleTS < min) {
            return;
          }
          const passed = startedAt && now - startedAt;
          return passed ? Math.round(bytesCount * 1e3 / passed) : void 0;
        };
      }
      function throttle(fn, freq) {
        let timestamp = 0;
        let threshold = 1e3 / freq;
        let lastArgs;
        let timer;
        const invoke = (args, now = Date.now()) => {
          timestamp = now;
          lastArgs = null;
          if (timer) {
            clearTimeout(timer);
            timer = null;
          }
          fn(...args);
        };
        const throttled = (...args) => {
          const now = Date.now();
          const passed = now - timestamp;
          if (passed >= threshold) {
            invoke(args, now);
          } else {
            lastArgs = args;
            if (!timer) {
              timer = setTimeout(() => {
                timer = null;
                invoke(lastArgs);
              }, threshold - passed);
            }
          }
        };
        const flush = () => lastArgs && invoke(lastArgs);
        return [throttled, flush];
      }
      var progressEventReducer = (listener, isDownloadStream, freq = 3) => {
        let bytesNotified = 0;
        const _speedometer = speedometer(50, 250);
        return throttle((e) => {
          const loaded = e.loaded;
          const total = e.lengthComputable ? e.total : void 0;
          const progressBytes = loaded - bytesNotified;
          const rate = _speedometer(progressBytes);
          const inRange = loaded <= total;
          bytesNotified = loaded;
          const data = {
            loaded,
            total,
            progress: total ? loaded / total : void 0,
            bytes: progressBytes,
            rate: rate ? rate : void 0,
            estimated: rate && total && inRange ? (total - loaded) / rate : void 0,
            event: e,
            lengthComputable: total != null,
            [isDownloadStream ? "download" : "upload"]: true
          };
          listener(data);
        }, freq);
      };
      var progressEventDecorator = (total, throttled) => {
        const lengthComputable = total != null;
        return [(loaded) => throttled[0]({
          lengthComputable,
          total,
          loaded
        }), throttled[1]];
      };
      var asyncDecorator = (fn) => (...args) => utils$1.asap(() => fn(...args));
      var isURLSameOrigin = platform.hasStandardBrowserEnv ? /* @__PURE__ */ ((origin2, isMSIE) => (url) => {
        url = new URL(url, platform.origin);
        return origin2.protocol === url.protocol && origin2.host === url.host && (isMSIE || origin2.port === url.port);
      })(
        new URL(platform.origin),
        platform.navigator && /(msie|trident)/i.test(platform.navigator.userAgent)
      ) : () => true;
      var cookies = platform.hasStandardBrowserEnv ? (
        // Standard browser envs support document.cookie
        {
          write(name, value, expires, path, domain, secure, sameSite) {
            if (typeof document === "undefined") return;
            const cookie = [`${name}=${encodeURIComponent(value)}`];
            if (utils$1.isNumber(expires)) {
              cookie.push(`expires=${new Date(expires).toUTCString()}`);
            }
            if (utils$1.isString(path)) {
              cookie.push(`path=${path}`);
            }
            if (utils$1.isString(domain)) {
              cookie.push(`domain=${domain}`);
            }
            if (secure === true) {
              cookie.push("secure");
            }
            if (utils$1.isString(sameSite)) {
              cookie.push(`SameSite=${sameSite}`);
            }
            document.cookie = cookie.join("; ");
          },
          read(name) {
            if (typeof document === "undefined") return null;
            const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
            return match ? decodeURIComponent(match[1]) : null;
          },
          remove(name) {
            this.write(name, "", Date.now() - 864e5, "/");
          }
        }
      ) : (
        // Non-standard browser env (web workers, react-native) lack needed support.
        {
          write() {
          },
          read() {
            return null;
          },
          remove() {
          }
        }
      );
      function isAbsoluteURL(url) {
        return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(url);
      }
      function combineURLs(baseURL, relativeURL) {
        return relativeURL ? baseURL.replace(/\/?\/$/, "") + "/" + relativeURL.replace(/^\/+/, "") : baseURL;
      }
      function buildFullPath(baseURL, requestedURL, allowAbsoluteUrls) {
        let isRelativeUrl = !isAbsoluteURL(requestedURL);
        if (baseURL && (isRelativeUrl || allowAbsoluteUrls == false)) {
          return combineURLs(baseURL, requestedURL);
        }
        return requestedURL;
      }
      var headersToObject = (thing) => thing instanceof AxiosHeaders$1 ? { ...thing } : thing;
      function mergeConfig(config1, config2) {
        config2 = config2 || {};
        const config = {};
        function getMergedValue(target, source, prop, caseless) {
          if (utils$1.isPlainObject(target) && utils$1.isPlainObject(source)) {
            return utils$1.merge.call({ caseless }, target, source);
          } else if (utils$1.isPlainObject(source)) {
            return utils$1.merge({}, source);
          } else if (utils$1.isArray(source)) {
            return source.slice();
          }
          return source;
        }
        function mergeDeepProperties(a, b, prop, caseless) {
          if (!utils$1.isUndefined(b)) {
            return getMergedValue(a, b, prop, caseless);
          } else if (!utils$1.isUndefined(a)) {
            return getMergedValue(void 0, a, prop, caseless);
          }
        }
        function valueFromConfig2(a, b) {
          if (!utils$1.isUndefined(b)) {
            return getMergedValue(void 0, b);
          }
        }
        function defaultToConfig2(a, b) {
          if (!utils$1.isUndefined(b)) {
            return getMergedValue(void 0, b);
          } else if (!utils$1.isUndefined(a)) {
            return getMergedValue(void 0, a);
          }
        }
        function mergeDirectKeys(a, b, prop) {
          if (prop in config2) {
            return getMergedValue(a, b);
          } else if (prop in config1) {
            return getMergedValue(void 0, a);
          }
        }
        const mergeMap = {
          url: valueFromConfig2,
          method: valueFromConfig2,
          data: valueFromConfig2,
          baseURL: defaultToConfig2,
          transformRequest: defaultToConfig2,
          transformResponse: defaultToConfig2,
          paramsSerializer: defaultToConfig2,
          timeout: defaultToConfig2,
          timeoutMessage: defaultToConfig2,
          withCredentials: defaultToConfig2,
          withXSRFToken: defaultToConfig2,
          adapter: defaultToConfig2,
          responseType: defaultToConfig2,
          xsrfCookieName: defaultToConfig2,
          xsrfHeaderName: defaultToConfig2,
          onUploadProgress: defaultToConfig2,
          onDownloadProgress: defaultToConfig2,
          decompress: defaultToConfig2,
          maxContentLength: defaultToConfig2,
          maxBodyLength: defaultToConfig2,
          beforeRedirect: defaultToConfig2,
          transport: defaultToConfig2,
          httpAgent: defaultToConfig2,
          httpsAgent: defaultToConfig2,
          cancelToken: defaultToConfig2,
          socketPath: defaultToConfig2,
          responseEncoding: defaultToConfig2,
          validateStatus: mergeDirectKeys,
          headers: (a, b, prop) => mergeDeepProperties(headersToObject(a), headersToObject(b), prop, true)
        };
        utils$1.forEach(Object.keys({ ...config1, ...config2 }), function computeConfigValue(prop) {
          const merge2 = mergeMap[prop] || mergeDeepProperties;
          const configValue = merge2(config1[prop], config2[prop], prop);
          utils$1.isUndefined(configValue) && merge2 !== mergeDirectKeys || (config[prop] = configValue);
        });
        return config;
      }
      var resolveConfig = (config) => {
        const newConfig = mergeConfig({}, config);
        let { data, withXSRFToken, xsrfHeaderName, xsrfCookieName, headers, auth } = newConfig;
        newConfig.headers = headers = AxiosHeaders$1.from(headers);
        newConfig.url = buildURL(buildFullPath(newConfig.baseURL, newConfig.url, newConfig.allowAbsoluteUrls), config.params, config.paramsSerializer);
        if (auth) {
          headers.set(
            "Authorization",
            "Basic " + btoa((auth.username || "") + ":" + (auth.password ? unescape(encodeURIComponent(auth.password)) : ""))
          );
        }
        if (utils$1.isFormData(data)) {
          if (platform.hasStandardBrowserEnv || platform.hasStandardBrowserWebWorkerEnv) {
            headers.setContentType(void 0);
          } else if (utils$1.isFunction(data.getHeaders)) {
            const formHeaders = data.getHeaders();
            const allowedHeaders = ["content-type", "content-length"];
            Object.entries(formHeaders).forEach(([key, val]) => {
              if (allowedHeaders.includes(key.toLowerCase())) {
                headers.set(key, val);
              }
            });
          }
        }
        if (platform.hasStandardBrowserEnv) {
          withXSRFToken && utils$1.isFunction(withXSRFToken) && (withXSRFToken = withXSRFToken(newConfig));
          if (withXSRFToken || withXSRFToken !== false && isURLSameOrigin(newConfig.url)) {
            const xsrfValue = xsrfHeaderName && xsrfCookieName && cookies.read(xsrfCookieName);
            if (xsrfValue) {
              headers.set(xsrfHeaderName, xsrfValue);
            }
          }
        }
        return newConfig;
      };
      var isXHRAdapterSupported = typeof XMLHttpRequest !== "undefined";
      var xhrAdapter = isXHRAdapterSupported && function(config) {
        return new Promise(function dispatchXhrRequest(resolve, reject) {
          const _config = resolveConfig(config);
          let requestData = _config.data;
          const requestHeaders = AxiosHeaders$1.from(_config.headers).normalize();
          let { responseType, onUploadProgress, onDownloadProgress } = _config;
          let onCanceled;
          let uploadThrottled, downloadThrottled;
          let flushUpload, flushDownload;
          function done() {
            flushUpload && flushUpload();
            flushDownload && flushDownload();
            _config.cancelToken && _config.cancelToken.unsubscribe(onCanceled);
            _config.signal && _config.signal.removeEventListener("abort", onCanceled);
          }
          let request = new XMLHttpRequest();
          request.open(_config.method.toUpperCase(), _config.url, true);
          request.timeout = _config.timeout;
          function onloadend() {
            if (!request) {
              return;
            }
            const responseHeaders = AxiosHeaders$1.from(
              "getAllResponseHeaders" in request && request.getAllResponseHeaders()
            );
            const responseData = !responseType || responseType === "text" || responseType === "json" ? request.responseText : request.response;
            const response = {
              data: responseData,
              status: request.status,
              statusText: request.statusText,
              headers: responseHeaders,
              config,
              request
            };
            settle(function _resolve(value) {
              resolve(value);
              done();
            }, function _reject(err) {
              reject(err);
              done();
            }, response);
            request = null;
          }
          if ("onloadend" in request) {
            request.onloadend = onloadend;
          } else {
            request.onreadystatechange = function handleLoad() {
              if (!request || request.readyState !== 4) {
                return;
              }
              if (request.status === 0 && !(request.responseURL && request.responseURL.indexOf("file:") === 0)) {
                return;
              }
              setTimeout(onloadend);
            };
          }
          request.onabort = function handleAbort() {
            if (!request) {
              return;
            }
            reject(new AxiosError("Request aborted", AxiosError.ECONNABORTED, config, request));
            request = null;
          };
          request.onerror = function handleError(event) {
            const msg = event && event.message ? event.message : "Network Error";
            const err = new AxiosError(msg, AxiosError.ERR_NETWORK, config, request);
            err.event = event || null;
            reject(err);
            request = null;
          };
          request.ontimeout = function handleTimeout() {
            let timeoutErrorMessage = _config.timeout ? "timeout of " + _config.timeout + "ms exceeded" : "timeout exceeded";
            const transitional = _config.transitional || transitionalDefaults;
            if (_config.timeoutErrorMessage) {
              timeoutErrorMessage = _config.timeoutErrorMessage;
            }
            reject(new AxiosError(
              timeoutErrorMessage,
              transitional.clarifyTimeoutError ? AxiosError.ETIMEDOUT : AxiosError.ECONNABORTED,
              config,
              request
            ));
            request = null;
          };
          requestData === void 0 && requestHeaders.setContentType(null);
          if ("setRequestHeader" in request) {
            utils$1.forEach(requestHeaders.toJSON(), function setRequestHeader(val, key) {
              request.setRequestHeader(key, val);
            });
          }
          if (!utils$1.isUndefined(_config.withCredentials)) {
            request.withCredentials = !!_config.withCredentials;
          }
          if (responseType && responseType !== "json") {
            request.responseType = _config.responseType;
          }
          if (onDownloadProgress) {
            [downloadThrottled, flushDownload] = progressEventReducer(onDownloadProgress, true);
            request.addEventListener("progress", downloadThrottled);
          }
          if (onUploadProgress && request.upload) {
            [uploadThrottled, flushUpload] = progressEventReducer(onUploadProgress);
            request.upload.addEventListener("progress", uploadThrottled);
            request.upload.addEventListener("loadend", flushUpload);
          }
          if (_config.cancelToken || _config.signal) {
            onCanceled = (cancel) => {
              if (!request) {
                return;
              }
              reject(!cancel || cancel.type ? new CanceledError(null, config, request) : cancel);
              request.abort();
              request = null;
            };
            _config.cancelToken && _config.cancelToken.subscribe(onCanceled);
            if (_config.signal) {
              _config.signal.aborted ? onCanceled() : _config.signal.addEventListener("abort", onCanceled);
            }
          }
          const protocol = parseProtocol(_config.url);
          if (protocol && platform.protocols.indexOf(protocol) === -1) {
            reject(new AxiosError("Unsupported protocol " + protocol + ":", AxiosError.ERR_BAD_REQUEST, config));
            return;
          }
          request.send(requestData || null);
        });
      };
      var composeSignals = (signals, timeout) => {
        const { length } = signals = signals ? signals.filter(Boolean) : [];
        if (timeout || length) {
          let controller = new AbortController();
          let aborted;
          const onabort = function(reason) {
            if (!aborted) {
              aborted = true;
              unsubscribe();
              const err = reason instanceof Error ? reason : this.reason;
              controller.abort(err instanceof AxiosError ? err : new CanceledError(err instanceof Error ? err.message : err));
            }
          };
          let timer = timeout && setTimeout(() => {
            timer = null;
            onabort(new AxiosError(`timeout ${timeout} of ms exceeded`, AxiosError.ETIMEDOUT));
          }, timeout);
          const unsubscribe = () => {
            if (signals) {
              timer && clearTimeout(timer);
              timer = null;
              signals.forEach((signal2) => {
                signal2.unsubscribe ? signal2.unsubscribe(onabort) : signal2.removeEventListener("abort", onabort);
              });
              signals = null;
            }
          };
          signals.forEach((signal2) => signal2.addEventListener("abort", onabort));
          const { signal } = controller;
          signal.unsubscribe = () => utils$1.asap(unsubscribe);
          return signal;
        }
      };
      var composeSignals$1 = composeSignals;
      var streamChunk = function* (chunk, chunkSize) {
        let len = chunk.byteLength;
        if (!chunkSize || len < chunkSize) {
          yield chunk;
          return;
        }
        let pos = 0;
        let end;
        while (pos < len) {
          end = pos + chunkSize;
          yield chunk.slice(pos, end);
          pos = end;
        }
      };
      var readBytes = async function* (iterable, chunkSize) {
        for await (const chunk of readStream(iterable)) {
          yield* streamChunk(chunk, chunkSize);
        }
      };
      var readStream = async function* (stream) {
        if (stream[Symbol.asyncIterator]) {
          yield* stream;
          return;
        }
        const reader = stream.getReader();
        try {
          for (; ; ) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }
            yield value;
          }
        } finally {
          await reader.cancel();
        }
      };
      var trackStream = (stream, chunkSize, onProgress, onFinish) => {
        const iterator2 = readBytes(stream, chunkSize);
        let bytes = 0;
        let done;
        let _onFinish = (e) => {
          if (!done) {
            done = true;
            onFinish && onFinish(e);
          }
        };
        return new ReadableStream({
          async pull(controller) {
            try {
              const { done: done2, value } = await iterator2.next();
              if (done2) {
                _onFinish();
                controller.close();
                return;
              }
              let len = value.byteLength;
              if (onProgress) {
                let loadedBytes = bytes += len;
                onProgress(loadedBytes);
              }
              controller.enqueue(new Uint8Array(value));
            } catch (err) {
              _onFinish(err);
              throw err;
            }
          },
          cancel(reason) {
            _onFinish(reason);
            return iterator2.return();
          }
        }, {
          highWaterMark: 2
        });
      };
      var DEFAULT_CHUNK_SIZE = 64 * 1024;
      var { isFunction } = utils$1;
      var globalFetchAPI = (({ Request, Response }) => ({
        Request,
        Response
      }))(utils$1.global);
      var {
        ReadableStream: ReadableStream$1,
        TextEncoder
      } = utils$1.global;
      var test = (fn, ...args) => {
        try {
          return !!fn(...args);
        } catch (e) {
          return false;
        }
      };
      var factory = (env) => {
        env = utils$1.merge.call({
          skipUndefined: true
        }, globalFetchAPI, env);
        const { fetch: envFetch, Request, Response } = env;
        const isFetchSupported = envFetch ? isFunction(envFetch) : typeof fetch === "function";
        const isRequestSupported = isFunction(Request);
        const isResponseSupported = isFunction(Response);
        if (!isFetchSupported) {
          return false;
        }
        const isReadableStreamSupported = isFetchSupported && isFunction(ReadableStream$1);
        const encodeText = isFetchSupported && (typeof TextEncoder === "function" ? /* @__PURE__ */ ((encoder) => (str) => encoder.encode(str))(new TextEncoder()) : async (str) => new Uint8Array(await new Request(str).arrayBuffer()));
        const supportsRequestStream = isRequestSupported && isReadableStreamSupported && test(() => {
          let duplexAccessed = false;
          const hasContentType = new Request(platform.origin, {
            body: new ReadableStream$1(),
            method: "POST",
            get duplex() {
              duplexAccessed = true;
              return "half";
            }
          }).headers.has("Content-Type");
          return duplexAccessed && !hasContentType;
        });
        const supportsResponseStream = isResponseSupported && isReadableStreamSupported && test(() => utils$1.isReadableStream(new Response("").body));
        const resolvers = {
          stream: supportsResponseStream && ((res) => res.body)
        };
        isFetchSupported && (() => {
          ["text", "arrayBuffer", "blob", "formData", "stream"].forEach((type2) => {
            !resolvers[type2] && (resolvers[type2] = (res, config) => {
              let method = res && res[type2];
              if (method) {
                return method.call(res);
              }
              throw new AxiosError(`Response type '${type2}' is not supported`, AxiosError.ERR_NOT_SUPPORT, config);
            });
          });
        })();
        const getBodyLength = async (body) => {
          if (body == null) {
            return 0;
          }
          if (utils$1.isBlob(body)) {
            return body.size;
          }
          if (utils$1.isSpecCompliantForm(body)) {
            const _request = new Request(platform.origin, {
              method: "POST",
              body
            });
            return (await _request.arrayBuffer()).byteLength;
          }
          if (utils$1.isArrayBufferView(body) || utils$1.isArrayBuffer(body)) {
            return body.byteLength;
          }
          if (utils$1.isURLSearchParams(body)) {
            body = body + "";
          }
          if (utils$1.isString(body)) {
            return (await encodeText(body)).byteLength;
          }
        };
        const resolveBodyLength = async (headers, body) => {
          const length = utils$1.toFiniteNumber(headers.getContentLength());
          return length == null ? getBodyLength(body) : length;
        };
        return async (config) => {
          let {
            url,
            method,
            data,
            signal,
            cancelToken,
            timeout,
            onDownloadProgress,
            onUploadProgress,
            responseType,
            headers,
            withCredentials = "same-origin",
            fetchOptions
          } = resolveConfig(config);
          let _fetch = envFetch || fetch;
          responseType = responseType ? (responseType + "").toLowerCase() : "text";
          let composedSignal = composeSignals$1([signal, cancelToken && cancelToken.toAbortSignal()], timeout);
          let request = null;
          const unsubscribe = composedSignal && composedSignal.unsubscribe && (() => {
            composedSignal.unsubscribe();
          });
          let requestContentLength;
          try {
            if (onUploadProgress && supportsRequestStream && method !== "get" && method !== "head" && (requestContentLength = await resolveBodyLength(headers, data)) !== 0) {
              let _request = new Request(url, {
                method: "POST",
                body: data,
                duplex: "half"
              });
              let contentTypeHeader;
              if (utils$1.isFormData(data) && (contentTypeHeader = _request.headers.get("content-type"))) {
                headers.setContentType(contentTypeHeader);
              }
              if (_request.body) {
                const [onProgress, flush] = progressEventDecorator(
                  requestContentLength,
                  progressEventReducer(asyncDecorator(onUploadProgress))
                );
                data = trackStream(_request.body, DEFAULT_CHUNK_SIZE, onProgress, flush);
              }
            }
            if (!utils$1.isString(withCredentials)) {
              withCredentials = withCredentials ? "include" : "omit";
            }
            const isCredentialsSupported = isRequestSupported && "credentials" in Request.prototype;
            const resolvedOptions = {
              ...fetchOptions,
              signal: composedSignal,
              method: method.toUpperCase(),
              headers: headers.normalize().toJSON(),
              body: data,
              duplex: "half",
              credentials: isCredentialsSupported ? withCredentials : void 0
            };
            request = isRequestSupported && new Request(url, resolvedOptions);
            let response = await (isRequestSupported ? _fetch(request, fetchOptions) : _fetch(url, resolvedOptions));
            const isStreamResponse = supportsResponseStream && (responseType === "stream" || responseType === "response");
            if (supportsResponseStream && (onDownloadProgress || isStreamResponse && unsubscribe)) {
              const options = {};
              ["status", "statusText", "headers"].forEach((prop) => {
                options[prop] = response[prop];
              });
              const responseContentLength = utils$1.toFiniteNumber(response.headers.get("content-length"));
              const [onProgress, flush] = onDownloadProgress && progressEventDecorator(
                responseContentLength,
                progressEventReducer(asyncDecorator(onDownloadProgress), true)
              ) || [];
              response = new Response(
                trackStream(response.body, DEFAULT_CHUNK_SIZE, onProgress, () => {
                  flush && flush();
                  unsubscribe && unsubscribe();
                }),
                options
              );
            }
            responseType = responseType || "text";
            let responseData = await resolvers[utils$1.findKey(resolvers, responseType) || "text"](response, config);
            !isStreamResponse && unsubscribe && unsubscribe();
            return await new Promise((resolve, reject) => {
              settle(resolve, reject, {
                data: responseData,
                headers: AxiosHeaders$1.from(response.headers),
                status: response.status,
                statusText: response.statusText,
                config,
                request
              });
            });
          } catch (err) {
            unsubscribe && unsubscribe();
            if (err && err.name === "TypeError" && /Load failed|fetch/i.test(err.message)) {
              throw Object.assign(
                new AxiosError("Network Error", AxiosError.ERR_NETWORK, config, request),
                {
                  cause: err.cause || err
                }
              );
            }
            throw AxiosError.from(err, err && err.code, config, request);
          }
        };
      };
      var seedCache = /* @__PURE__ */ new Map();
      var getFetch = (config) => {
        let env = config && config.env || {};
        const { fetch: fetch2, Request, Response } = env;
        const seeds = [
          Request,
          Response,
          fetch2
        ];
        let len = seeds.length, i = len, seed, target, map = seedCache;
        while (i--) {
          seed = seeds[i];
          target = map.get(seed);
          target === void 0 && map.set(seed, target = i ? /* @__PURE__ */ new Map() : factory(env));
          map = target;
        }
        return target;
      };
      getFetch();
      var knownAdapters = {
        http: httpAdapter,
        xhr: xhrAdapter,
        fetch: {
          get: getFetch
        }
      };
      utils$1.forEach(knownAdapters, (fn, value) => {
        if (fn) {
          try {
            Object.defineProperty(fn, "name", { value });
          } catch (e) {
          }
          Object.defineProperty(fn, "adapterName", { value });
        }
      });
      var renderReason = (reason) => `- ${reason}`;
      var isResolvedHandle = (adapter) => utils$1.isFunction(adapter) || adapter === null || adapter === false;
      function getAdapter(adapters2, config) {
        adapters2 = utils$1.isArray(adapters2) ? adapters2 : [adapters2];
        const { length } = adapters2;
        let nameOrAdapter;
        let adapter;
        const rejectedReasons = {};
        for (let i = 0; i < length; i++) {
          nameOrAdapter = adapters2[i];
          let id;
          adapter = nameOrAdapter;
          if (!isResolvedHandle(nameOrAdapter)) {
            adapter = knownAdapters[(id = String(nameOrAdapter)).toLowerCase()];
            if (adapter === void 0) {
              throw new AxiosError(`Unknown adapter '${id}'`);
            }
          }
          if (adapter && (utils$1.isFunction(adapter) || (adapter = adapter.get(config)))) {
            break;
          }
          rejectedReasons[id || "#" + i] = adapter;
        }
        if (!adapter) {
          const reasons = Object.entries(rejectedReasons).map(
            ([id, state2]) => `adapter ${id} ` + (state2 === false ? "is not supported by the environment" : "is not available in the build")
          );
          let s = length ? reasons.length > 1 ? "since :\n" + reasons.map(renderReason).join("\n") : " " + renderReason(reasons[0]) : "as no adapter specified";
          throw new AxiosError(
            `There is no suitable adapter to dispatch the request ` + s,
            "ERR_NOT_SUPPORT"
          );
        }
        return adapter;
      }
      var adapters = {
        /**
         * Resolve an adapter from a list of adapter names or functions.
         * @type {Function}
         */
        getAdapter,
        /**
         * Exposes all known adapters
         * @type {Object<string, Function|Object>}
         */
        adapters: knownAdapters
      };
      function throwIfCancellationRequested(config) {
        if (config.cancelToken) {
          config.cancelToken.throwIfRequested();
        }
        if (config.signal && config.signal.aborted) {
          throw new CanceledError(null, config);
        }
      }
      function dispatchRequest(config) {
        throwIfCancellationRequested(config);
        config.headers = AxiosHeaders$1.from(config.headers);
        config.data = transformData.call(
          config,
          config.transformRequest
        );
        if (["post", "put", "patch"].indexOf(config.method) !== -1) {
          config.headers.setContentType("application/x-www-form-urlencoded", false);
        }
        const adapter = adapters.getAdapter(config.adapter || defaults$1.adapter, config);
        return adapter(config).then(function onAdapterResolution(response) {
          throwIfCancellationRequested(config);
          response.data = transformData.call(
            config,
            config.transformResponse,
            response
          );
          response.headers = AxiosHeaders$1.from(response.headers);
          return response;
        }, function onAdapterRejection(reason) {
          if (!isCancel(reason)) {
            throwIfCancellationRequested(config);
            if (reason && reason.response) {
              reason.response.data = transformData.call(
                config,
                config.transformResponse,
                reason.response
              );
              reason.response.headers = AxiosHeaders$1.from(reason.response.headers);
            }
          }
          return Promise.reject(reason);
        });
      }
      var VERSION = "1.13.2";
      var validators$1 = {};
      ["object", "boolean", "number", "function", "string", "symbol"].forEach((type2, i) => {
        validators$1[type2] = function validator2(thing) {
          return typeof thing === type2 || "a" + (i < 1 ? "n " : " ") + type2;
        };
      });
      var deprecatedWarnings = {};
      validators$1.transitional = function transitional(validator2, version, message) {
        function formatMessage(opt, desc) {
          return "[Axios v" + VERSION + "] Transitional option '" + opt + "'" + desc + (message ? ". " + message : "");
        }
        return (value, opt, opts) => {
          if (validator2 === false) {
            throw new AxiosError(
              formatMessage(opt, " has been removed" + (version ? " in " + version : "")),
              AxiosError.ERR_DEPRECATED
            );
          }
          if (version && !deprecatedWarnings[opt]) {
            deprecatedWarnings[opt] = true;
            console.warn(
              formatMessage(
                opt,
                " has been deprecated since v" + version + " and will be removed in the near future"
              )
            );
          }
          return validator2 ? validator2(value, opt, opts) : true;
        };
      };
      validators$1.spelling = function spelling(correctSpelling) {
        return (value, opt) => {
          console.warn(`${opt} is likely a misspelling of ${correctSpelling}`);
          return true;
        };
      };
      function assertOptions(options, schema, allowUnknown) {
        if (typeof options !== "object") {
          throw new AxiosError("options must be an object", AxiosError.ERR_BAD_OPTION_VALUE);
        }
        const keys2 = Object.keys(options);
        let i = keys2.length;
        while (i-- > 0) {
          const opt = keys2[i];
          const validator2 = schema[opt];
          if (validator2) {
            const value = options[opt];
            const result = value === void 0 || validator2(value, opt, options);
            if (result !== true) {
              throw new AxiosError("option " + opt + " must be " + result, AxiosError.ERR_BAD_OPTION_VALUE);
            }
            continue;
          }
          if (allowUnknown !== true) {
            throw new AxiosError("Unknown option " + opt, AxiosError.ERR_BAD_OPTION);
          }
        }
      }
      var validator = {
        assertOptions,
        validators: validators$1
      };
      var validators = validator.validators;
      var Axios = class {
        constructor(instanceConfig) {
          this.defaults = instanceConfig || {};
          this.interceptors = {
            request: new InterceptorManager$1(),
            response: new InterceptorManager$1()
          };
        }
        /**
         * Dispatch a request
         *
         * @param {String|Object} configOrUrl The config specific for this request (merged with this.defaults)
         * @param {?Object} config
         *
         * @returns {Promise} The Promise to be fulfilled
         */
        async request(configOrUrl, config) {
          try {
            return await this._request(configOrUrl, config);
          } catch (err) {
            if (err instanceof Error) {
              let dummy = {};
              Error.captureStackTrace ? Error.captureStackTrace(dummy) : dummy = new Error();
              const stack = dummy.stack ? dummy.stack.replace(/^.+\n/, "") : "";
              try {
                if (!err.stack) {
                  err.stack = stack;
                } else if (stack && !String(err.stack).endsWith(stack.replace(/^.+\n.+\n/, ""))) {
                  err.stack += "\n" + stack;
                }
              } catch (e) {
              }
            }
            throw err;
          }
        }
        _request(configOrUrl, config) {
          if (typeof configOrUrl === "string") {
            config = config || {};
            config.url = configOrUrl;
          } else {
            config = configOrUrl || {};
          }
          config = mergeConfig(this.defaults, config);
          const { transitional, paramsSerializer, headers } = config;
          if (transitional !== void 0) {
            validator.assertOptions(transitional, {
              silentJSONParsing: validators.transitional(validators.boolean),
              forcedJSONParsing: validators.transitional(validators.boolean),
              clarifyTimeoutError: validators.transitional(validators.boolean)
            }, false);
          }
          if (paramsSerializer != null) {
            if (utils$1.isFunction(paramsSerializer)) {
              config.paramsSerializer = {
                serialize: paramsSerializer
              };
            } else {
              validator.assertOptions(paramsSerializer, {
                encode: validators.function,
                serialize: validators.function
              }, true);
            }
          }
          if (config.allowAbsoluteUrls !== void 0) ;
          else if (this.defaults.allowAbsoluteUrls !== void 0) {
            config.allowAbsoluteUrls = this.defaults.allowAbsoluteUrls;
          } else {
            config.allowAbsoluteUrls = true;
          }
          validator.assertOptions(config, {
            baseUrl: validators.spelling("baseURL"),
            withXsrfToken: validators.spelling("withXSRFToken")
          }, true);
          config.method = (config.method || this.defaults.method || "get").toLowerCase();
          let contextHeaders = headers && utils$1.merge(
            headers.common,
            headers[config.method]
          );
          headers && utils$1.forEach(
            ["delete", "get", "head", "post", "put", "patch", "common"],
            (method) => {
              delete headers[method];
            }
          );
          config.headers = AxiosHeaders$1.concat(contextHeaders, headers);
          const requestInterceptorChain = [];
          let synchronousRequestInterceptors = true;
          this.interceptors.request.forEach(function unshiftRequestInterceptors(interceptor) {
            if (typeof interceptor.runWhen === "function" && interceptor.runWhen(config) === false) {
              return;
            }
            synchronousRequestInterceptors = synchronousRequestInterceptors && interceptor.synchronous;
            requestInterceptorChain.unshift(interceptor.fulfilled, interceptor.rejected);
          });
          const responseInterceptorChain = [];
          this.interceptors.response.forEach(function pushResponseInterceptors(interceptor) {
            responseInterceptorChain.push(interceptor.fulfilled, interceptor.rejected);
          });
          let promise;
          let i = 0;
          let len;
          if (!synchronousRequestInterceptors) {
            const chain = [dispatchRequest.bind(this), void 0];
            chain.unshift(...requestInterceptorChain);
            chain.push(...responseInterceptorChain);
            len = chain.length;
            promise = Promise.resolve(config);
            while (i < len) {
              promise = promise.then(chain[i++], chain[i++]);
            }
            return promise;
          }
          len = requestInterceptorChain.length;
          let newConfig = config;
          while (i < len) {
            const onFulfilled = requestInterceptorChain[i++];
            const onRejected = requestInterceptorChain[i++];
            try {
              newConfig = onFulfilled(newConfig);
            } catch (error) {
              onRejected.call(this, error);
              break;
            }
          }
          try {
            promise = dispatchRequest.call(this, newConfig);
          } catch (error) {
            return Promise.reject(error);
          }
          i = 0;
          len = responseInterceptorChain.length;
          while (i < len) {
            promise = promise.then(responseInterceptorChain[i++], responseInterceptorChain[i++]);
          }
          return promise;
        }
        getUri(config) {
          config = mergeConfig(this.defaults, config);
          const fullPath = buildFullPath(config.baseURL, config.url, config.allowAbsoluteUrls);
          return buildURL(fullPath, config.params, config.paramsSerializer);
        }
      };
      utils$1.forEach(["delete", "get", "head", "options"], function forEachMethodNoData(method) {
        Axios.prototype[method] = function(url, config) {
          return this.request(mergeConfig(config || {}, {
            method,
            url,
            data: (config || {}).data
          }));
        };
      });
      utils$1.forEach(["post", "put", "patch"], function forEachMethodWithData(method) {
        function generateHTTPMethod(isForm) {
          return function httpMethod(url, data, config) {
            return this.request(mergeConfig(config || {}, {
              method,
              headers: isForm ? {
                "Content-Type": "multipart/form-data"
              } : {},
              url,
              data
            }));
          };
        }
        Axios.prototype[method] = generateHTTPMethod();
        Axios.prototype[method + "Form"] = generateHTTPMethod(true);
      });
      var Axios$1 = Axios;
      var CancelToken = class _CancelToken {
        constructor(executor) {
          if (typeof executor !== "function") {
            throw new TypeError("executor must be a function.");
          }
          let resolvePromise;
          this.promise = new Promise(function promiseExecutor(resolve) {
            resolvePromise = resolve;
          });
          const token = this;
          this.promise.then((cancel) => {
            if (!token._listeners) return;
            let i = token._listeners.length;
            while (i-- > 0) {
              token._listeners[i](cancel);
            }
            token._listeners = null;
          });
          this.promise.then = (onfulfilled) => {
            let _resolve;
            const promise = new Promise((resolve) => {
              token.subscribe(resolve);
              _resolve = resolve;
            }).then(onfulfilled);
            promise.cancel = function reject() {
              token.unsubscribe(_resolve);
            };
            return promise;
          };
          executor(function cancel(message, config, request) {
            if (token.reason) {
              return;
            }
            token.reason = new CanceledError(message, config, request);
            resolvePromise(token.reason);
          });
        }
        /**
         * Throws a `CanceledError` if cancellation has been requested.
         */
        throwIfRequested() {
          if (this.reason) {
            throw this.reason;
          }
        }
        /**
         * Subscribe to the cancel signal
         */
        subscribe(listener) {
          if (this.reason) {
            listener(this.reason);
            return;
          }
          if (this._listeners) {
            this._listeners.push(listener);
          } else {
            this._listeners = [listener];
          }
        }
        /**
         * Unsubscribe from the cancel signal
         */
        unsubscribe(listener) {
          if (!this._listeners) {
            return;
          }
          const index = this._listeners.indexOf(listener);
          if (index !== -1) {
            this._listeners.splice(index, 1);
          }
        }
        toAbortSignal() {
          const controller = new AbortController();
          const abort = (err) => {
            controller.abort(err);
          };
          this.subscribe(abort);
          controller.signal.unsubscribe = () => this.unsubscribe(abort);
          return controller.signal;
        }
        /**
         * Returns an object that contains a new `CancelToken` and a function that, when called,
         * cancels the `CancelToken`.
         */
        static source() {
          let cancel;
          const token = new _CancelToken(function executor(c) {
            cancel = c;
          });
          return {
            token,
            cancel
          };
        }
      };
      var CancelToken$1 = CancelToken;
      function spread(callback) {
        return function wrap2(arr) {
          return callback.apply(null, arr);
        };
      }
      function isAxiosError(payload) {
        return utils$1.isObject(payload) && payload.isAxiosError === true;
      }
      var HttpStatusCode = {
        Continue: 100,
        SwitchingProtocols: 101,
        Processing: 102,
        EarlyHints: 103,
        Ok: 200,
        Created: 201,
        Accepted: 202,
        NonAuthoritativeInformation: 203,
        NoContent: 204,
        ResetContent: 205,
        PartialContent: 206,
        MultiStatus: 207,
        AlreadyReported: 208,
        ImUsed: 226,
        MultipleChoices: 300,
        MovedPermanently: 301,
        Found: 302,
        SeeOther: 303,
        NotModified: 304,
        UseProxy: 305,
        Unused: 306,
        TemporaryRedirect: 307,
        PermanentRedirect: 308,
        BadRequest: 400,
        Unauthorized: 401,
        PaymentRequired: 402,
        Forbidden: 403,
        NotFound: 404,
        MethodNotAllowed: 405,
        NotAcceptable: 406,
        ProxyAuthenticationRequired: 407,
        RequestTimeout: 408,
        Conflict: 409,
        Gone: 410,
        LengthRequired: 411,
        PreconditionFailed: 412,
        PayloadTooLarge: 413,
        UriTooLong: 414,
        UnsupportedMediaType: 415,
        RangeNotSatisfiable: 416,
        ExpectationFailed: 417,
        ImATeapot: 418,
        MisdirectedRequest: 421,
        UnprocessableEntity: 422,
        Locked: 423,
        FailedDependency: 424,
        TooEarly: 425,
        UpgradeRequired: 426,
        PreconditionRequired: 428,
        TooManyRequests: 429,
        RequestHeaderFieldsTooLarge: 431,
        UnavailableForLegalReasons: 451,
        InternalServerError: 500,
        NotImplemented: 501,
        BadGateway: 502,
        ServiceUnavailable: 503,
        GatewayTimeout: 504,
        HttpVersionNotSupported: 505,
        VariantAlsoNegotiates: 506,
        InsufficientStorage: 507,
        LoopDetected: 508,
        NotExtended: 510,
        NetworkAuthenticationRequired: 511,
        WebServerIsDown: 521,
        ConnectionTimedOut: 522,
        OriginIsUnreachable: 523,
        TimeoutOccurred: 524,
        SslHandshakeFailed: 525,
        InvalidSslCertificate: 526
      };
      Object.entries(HttpStatusCode).forEach(([key, value]) => {
        HttpStatusCode[value] = key;
      });
      var HttpStatusCode$1 = HttpStatusCode;
      function createInstance(defaultConfig) {
        const context = new Axios$1(defaultConfig);
        const instance = bind(Axios$1.prototype.request, context);
        utils$1.extend(instance, Axios$1.prototype, context, { allOwnKeys: true });
        utils$1.extend(instance, context, null, { allOwnKeys: true });
        instance.create = function create(instanceConfig) {
          return createInstance(mergeConfig(defaultConfig, instanceConfig));
        };
        return instance;
      }
      var axios = createInstance(defaults$1);
      axios.Axios = Axios$1;
      axios.CanceledError = CanceledError;
      axios.CancelToken = CancelToken$1;
      axios.isCancel = isCancel;
      axios.VERSION = VERSION;
      axios.toFormData = toFormData;
      axios.AxiosError = AxiosError;
      axios.Cancel = axios.CanceledError;
      axios.all = function all(promises) {
        return Promise.all(promises);
      };
      axios.spread = spread;
      axios.isAxiosError = isAxiosError;
      axios.mergeConfig = mergeConfig;
      axios.AxiosHeaders = AxiosHeaders$1;
      axios.formToJSON = (thing) => formDataToJSON(utils$1.isHTMLForm(thing) ? new FormData(thing) : thing);
      axios.getAdapter = adapters.getAdapter;
      axios.HttpStatusCode = HttpStatusCode$1;
      axios.default = axios;
      module.exports = axios;
    }
  });

  // src/shared/config.js
  var require_config = __commonJS({
    "src/shared/config.js"(exports, module) {
      var storeGet2 = async (key) => {
        if (window.electronAPI) {
          return await window.electronAPI.storeGet(key);
        }
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : null;
      };
      var storeSet2 = async (key, value) => {
        if (window.electronAPI) {
          return await window.electronAPI.storeSet(key, value);
        }
        localStorage.setItem(key, JSON.stringify(value));
      };
      var storeDelete2 = async (key) => {
        if (window.electronAPI) {
          return await window.electronAPI.storeDelete(key);
        }
        localStorage.removeItem(key);
      };
      var storeClear2 = async () => {
        if (window.electronAPI) {
          return await window.electronAPI.storeClear();
        }
        localStorage.clear();
      };
      if (typeof module !== "undefined" && module.exports) {
        module.exports = { storeGet: storeGet2, storeSet: storeSet2, storeDelete: storeDelete2, storeClear: storeClear2 };
      }
      if (typeof window !== "undefined") {
        window.config = { storeGet: storeGet2, storeSet: storeSet2, storeDelete: storeDelete2, storeClear: storeClear2 };
      }
    }
  });

  // src/renderer/js/api/client.js
  var require_client = __commonJS({
    "src/renderer/js/api/client.js"(exports, module) {
      var axios = require_axios();
      var cfg = typeof window !== "undefined" && window.config ? window.config : function() {
        try {
          return require_config();
        } catch (_) {
          return {};
        }
      }();
      var storeGet2 = cfg.storeGet || (async (k) => null);
      var storeSet2 = cfg.storeSet || (async (k, v) => {
      });
      var ApiClient2 = class {
        constructor(baseUrl) {
          this.baseUrl = baseUrl;
          this.client = axios.create({
            baseURL: baseUrl,
            timeout: 1e4,
            headers: {
              "Content-Type": "application/json",
              "Accept": "application/json"
            }
          });
          this.setupInterceptors();
        }
        setupInterceptors() {
          this.client.interceptors.request.use(async (config) => {
            const token = await storeGet2("api_token");
            if (token) {
              config.headers["Authorization"] = `Bearer ${token}`;
            }
            return config;
          });
          this.client.interceptors.response.use(
            (response) => response,
            (error) => {
              if (error.response) {
                const status = error.response.status;
                const data = error.response.data;
                if (status === 401) {
                  error.message = "Authentication failed. Please check your API token.";
                } else if (status === 403) {
                  error.message = "Access denied. Your token may not have the required permissions.";
                } else if (status === 404) {
                  error.message = data?.error || "Resource not found.";
                } else if (status >= 500) {
                  error.message = "Server error. Please try again later.";
                } else if (data?.error) {
                  error.message = data.error;
                }
              } else if (error.code === "ECONNABORTED") {
                error.message = "Request timeout. Please check your internet connection.";
              } else if (error.code === "ENOTFOUND" || error.code === "ECONNREFUSED") {
                error.message = "Unable to connect to server. Please check the server URL and your internet connection.";
              }
              return Promise.reject(error);
            }
          );
        }
        async setAuthToken(token) {
          await storeSet2("api_token", token);
        }
        async validateToken() {
          try {
            const response = await this.client.get("/api/v1/info");
            return response.status === 200;
          } catch (error) {
            return false;
          }
        }
        async getUsersMe() {
          const response = await this.client.get("/api/v1/users/me");
          return response.data;
        }
        // Timer endpoints
        async getTimerStatus() {
          return await this.client.get("/api/v1/timer/status");
        }
        async startTimer({ projectId, taskId, notes }) {
          return await this.client.post("/api/v1/timer/start", {
            project_id: projectId,
            task_id: taskId,
            notes
          });
        }
        async stopTimer() {
          return await this.client.post("/api/v1/timer/stop");
        }
        // Time entries endpoints
        async getTimeEntries({ projectId, startDate, endDate, billable, page, perPage }) {
          const params = {};
          if (projectId) params.project_id = projectId;
          if (startDate) params.start_date = startDate;
          if (endDate) params.end_date = endDate;
          if (billable !== void 0) params.billable = billable;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/time-entries", { params });
        }
        async createTimeEntry(data) {
          return await this.client.post("/api/v1/time-entries", data);
        }
        async updateTimeEntry(id, data) {
          return await this.client.put(`/api/v1/time-entries/${id}`, data);
        }
        async deleteTimeEntry(id) {
          return await this.client.delete(`/api/v1/time-entries/${id}`);
        }
        // Projects endpoints
        async getProjects({ status, clientId, page, perPage }) {
          const params = {};
          if (status) params.status = status;
          if (clientId) params.client_id = clientId;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/projects", { params });
        }
        async getProject(id) {
          return await this.client.get(`/api/v1/projects/${id}`);
        }
        async getClients({ status, page, perPage }) {
          const params = {};
          if (status) params.status = status;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/clients", { params });
        }
        // Tasks endpoints
        async getTasks({ projectId, status, page, perPage }) {
          const params = {};
          if (projectId) params.project_id = projectId;
          if (status) params.status = status;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/tasks", { params });
        }
        async getTask(id) {
          return await this.client.get(`/api/v1/tasks/${id}`);
        }
        // Get time entry by ID
        async getTimeEntry(id) {
          return await this.client.get(`/api/v1/time-entries/${id}`);
        }
        // Invoices endpoints
        async getInvoices({ status, clientId, projectId, page, perPage }) {
          const params = {};
          if (status) params.status = status;
          if (clientId) params.client_id = clientId;
          if (projectId) params.project_id = projectId;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/invoices", { params });
        }
        async getInvoice(id) {
          return await this.client.get(`/api/v1/invoices/${id}`);
        }
        async createInvoice(data) {
          return await this.client.post("/api/v1/invoices", data);
        }
        async updateInvoice(id, data) {
          return await this.client.put(`/api/v1/invoices/${id}`, data);
        }
        // Expenses endpoints
        async getExpenses({ projectId, category, startDate, endDate, page, perPage }) {
          const params = {};
          if (projectId) params.project_id = projectId;
          if (category) params.category = category;
          if (startDate) params.start_date = startDate;
          if (endDate) params.end_date = endDate;
          if (page) params.page = page;
          if (perPage) params.per_page = perPage;
          return await this.client.get("/api/v1/expenses", { params });
        }
        async createExpense(data) {
          return await this.client.post("/api/v1/expenses", data);
        }
        async getCapacityReport({ startDate, endDate }) {
          return await this.client.get("/api/v1/reports/capacity", {
            params: { start_date: startDate, end_date: endDate }
          });
        }
        async getTimesheetPeriods({ status, startDate, endDate }) {
          const params = {};
          if (status) params.status = status;
          if (startDate) params.start_date = startDate;
          if (endDate) params.end_date = endDate;
          return await this.client.get("/api/v1/timesheet-periods", { params });
        }
        async submitTimesheetPeriod(periodId) {
          return await this.client.post(`/api/v1/timesheet-periods/${periodId}/submit`);
        }
        async approveTimesheetPeriod(periodId, { comment } = {}) {
          const data = {};
          if (comment) data.comment = comment;
          return await this.client.post(`/api/v1/timesheet-periods/${periodId}/approve`, data);
        }
        async rejectTimesheetPeriod(periodId, { reason } = {}) {
          const data = {};
          if (reason) data.reason = reason;
          return await this.client.post(`/api/v1/timesheet-periods/${periodId}/reject`, data);
        }
        async getLeaveTypes() {
          return await this.client.get("/api/v1/time-off/leave-types");
        }
        async getTimeOffRequests({ status, startDate, endDate }) {
          const params = {};
          if (status) params.status = status;
          if (startDate) params.start_date = startDate;
          if (endDate) params.end_date = endDate;
          return await this.client.get("/api/v1/time-off/requests", { params });
        }
        async createTimeOffRequest({ leaveTypeId, startDate, endDate, requestedHours, comment, submit }) {
          const data = {
            leave_type_id: leaveTypeId,
            start_date: startDate,
            end_date: endDate,
            submit: submit !== void 0 ? submit : true
          };
          if (requestedHours !== void 0 && requestedHours !== null) data.requested_hours = requestedHours;
          if (comment) data.comment = comment;
          return await this.client.post("/api/v1/time-off/requests", data);
        }
        async getTimeOffBalances({ userId } = {}) {
          const params = {};
          if (userId) params.user_id = userId;
          return await this.client.get("/api/v1/time-off/balances", { params });
        }
        async approveTimeOffRequest(requestId, { comment } = {}) {
          const data = {};
          if (comment) data.comment = comment;
          return await this.client.post(`/api/v1/time-off/requests/${requestId}/approve`, data);
        }
        async rejectTimeOffRequest(requestId, { comment } = {}) {
          const data = {};
          if (comment) data.comment = comment;
          return await this.client.post(`/api/v1/time-off/requests/${requestId}/reject`, data);
        }
      };
      if (typeof module !== "undefined" && module.exports) {
        module.exports = ApiClient2;
      }
    }
  });

  // node_modules/dexie/dist/modern/dexie.mjs
  var dexie_exports = {};
  __export(dexie_exports, {
    Dexie: () => Dexie$1,
    RangeSet: () => RangeSet,
    default: () => Dexie$1,
    liveQuery: () => liveQuery,
    mergeRanges: () => mergeRanges,
    rangesOverlap: () => rangesOverlap
  });
  function extend(obj, extension) {
    if (typeof extension !== "object")
      return obj;
    keys(extension).forEach(function(key) {
      obj[key] = extension[key];
    });
    return obj;
  }
  function hasOwn(obj, prop) {
    return _hasOwn.call(obj, prop);
  }
  function props(proto, extension) {
    if (typeof extension === "function")
      extension = extension(getProto(proto));
    (typeof Reflect === "undefined" ? keys : Reflect.ownKeys)(extension).forEach((key) => {
      setProp(proto, key, extension[key]);
    });
  }
  function setProp(obj, prop, functionOrGetSet, options) {
    defineProperty(obj, prop, extend(functionOrGetSet && hasOwn(functionOrGetSet, "get") && typeof functionOrGetSet.get === "function" ? { get: functionOrGetSet.get, set: functionOrGetSet.set, configurable: true } : { value: functionOrGetSet, configurable: true, writable: true }, options));
  }
  function derive(Child) {
    return {
      from: function(Parent) {
        Child.prototype = Object.create(Parent.prototype);
        setProp(Child.prototype, "constructor", Child);
        return {
          extend: props.bind(null, Child.prototype)
        };
      }
    };
  }
  function getPropertyDescriptor(obj, prop) {
    const pd = getOwnPropertyDescriptor(obj, prop);
    let proto;
    return pd || (proto = getProto(obj)) && getPropertyDescriptor(proto, prop);
  }
  function slice(args, start, end) {
    return _slice.call(args, start, end);
  }
  function override(origFunc, overridedFactory) {
    return overridedFactory(origFunc);
  }
  function assert(b) {
    if (!b)
      throw new Error("Assertion Failed");
  }
  function asap$1(fn) {
    if (_global.setImmediate)
      setImmediate(fn);
    else
      setTimeout(fn, 0);
  }
  function arrayToObject(array, extractor) {
    return array.reduce((result, item, i) => {
      var nameAndValue = extractor(item, i);
      if (nameAndValue)
        result[nameAndValue[0]] = nameAndValue[1];
      return result;
    }, {});
  }
  function tryCatch(fn, onerror, args) {
    try {
      fn.apply(null, args);
    } catch (ex) {
      onerror && onerror(ex);
    }
  }
  function getByKeyPath(obj, keyPath) {
    if (typeof keyPath === "string" && hasOwn(obj, keyPath))
      return obj[keyPath];
    if (!keyPath)
      return obj;
    if (typeof keyPath !== "string") {
      var rv = [];
      for (var i = 0, l = keyPath.length; i < l; ++i) {
        var val = getByKeyPath(obj, keyPath[i]);
        rv.push(val);
      }
      return rv;
    }
    var period = keyPath.indexOf(".");
    if (period !== -1) {
      var innerObj = obj[keyPath.substr(0, period)];
      return innerObj == null ? void 0 : getByKeyPath(innerObj, keyPath.substr(period + 1));
    }
    return void 0;
  }
  function setByKeyPath(obj, keyPath, value) {
    if (!obj || keyPath === void 0)
      return;
    if ("isFrozen" in Object && Object.isFrozen(obj))
      return;
    if (typeof keyPath !== "string" && "length" in keyPath) {
      assert(typeof value !== "string" && "length" in value);
      for (var i = 0, l = keyPath.length; i < l; ++i) {
        setByKeyPath(obj, keyPath[i], value[i]);
      }
    } else {
      var period = keyPath.indexOf(".");
      if (period !== -1) {
        var currentKeyPath = keyPath.substr(0, period);
        var remainingKeyPath = keyPath.substr(period + 1);
        if (remainingKeyPath === "")
          if (value === void 0) {
            if (isArray(obj) && !isNaN(parseInt(currentKeyPath)))
              obj.splice(currentKeyPath, 1);
            else
              delete obj[currentKeyPath];
          } else
            obj[currentKeyPath] = value;
        else {
          var innerObj = obj[currentKeyPath];
          if (!innerObj || !hasOwn(obj, currentKeyPath))
            innerObj = obj[currentKeyPath] = {};
          setByKeyPath(innerObj, remainingKeyPath, value);
        }
      } else {
        if (value === void 0) {
          if (isArray(obj) && !isNaN(parseInt(keyPath)))
            obj.splice(keyPath, 1);
          else
            delete obj[keyPath];
        } else
          obj[keyPath] = value;
      }
    }
  }
  function delByKeyPath(obj, keyPath) {
    if (typeof keyPath === "string")
      setByKeyPath(obj, keyPath, void 0);
    else if ("length" in keyPath)
      [].map.call(keyPath, function(kp) {
        setByKeyPath(obj, kp, void 0);
      });
  }
  function shallowClone(obj) {
    var rv = {};
    for (var m in obj) {
      if (hasOwn(obj, m))
        rv[m] = obj[m];
    }
    return rv;
  }
  function flatten(a) {
    return concat.apply([], a);
  }
  function deepClone(any) {
    circularRefs = typeof WeakMap !== "undefined" && /* @__PURE__ */ new WeakMap();
    const rv = innerDeepClone(any);
    circularRefs = null;
    return rv;
  }
  function innerDeepClone(any) {
    if (!any || typeof any !== "object")
      return any;
    let rv = circularRefs && circularRefs.get(any);
    if (rv)
      return rv;
    if (isArray(any)) {
      rv = [];
      circularRefs && circularRefs.set(any, rv);
      for (var i = 0, l = any.length; i < l; ++i) {
        rv.push(innerDeepClone(any[i]));
      }
    } else if (intrinsicTypes.indexOf(any.constructor) >= 0) {
      rv = any;
    } else {
      const proto = getProto(any);
      rv = proto === Object.prototype ? {} : Object.create(proto);
      circularRefs && circularRefs.set(any, rv);
      for (var prop in any) {
        if (hasOwn(any, prop)) {
          rv[prop] = innerDeepClone(any[prop]);
        }
      }
    }
    return rv;
  }
  function toStringTag(o) {
    return toString.call(o).slice(8, -1);
  }
  function getArrayOf(arrayLike) {
    var i, a, x, it;
    if (arguments.length === 1) {
      if (isArray(arrayLike))
        return arrayLike.slice();
      if (this === NO_CHAR_ARRAY && typeof arrayLike === "string")
        return [arrayLike];
      if (it = getIteratorOf(arrayLike)) {
        a = [];
        while (x = it.next(), !x.done)
          a.push(x.value);
        return a;
      }
      if (arrayLike == null)
        return [arrayLike];
      i = arrayLike.length;
      if (typeof i === "number") {
        a = new Array(i);
        while (i--)
          a[i] = arrayLike[i];
        return a;
      }
      return [arrayLike];
    }
    i = arguments.length;
    a = new Array(i);
    while (i--)
      a[i] = arguments[i];
    return a;
  }
  function setDebug(value, filter) {
    debug = value;
    libraryFilter = filter;
  }
  function getErrorWithStack() {
    if (NEEDS_THROW_FOR_STACK)
      try {
        getErrorWithStack.arguments;
        throw new Error();
      } catch (e) {
        return e;
      }
    return new Error();
  }
  function prettyStack(exception, numIgnoredFrames) {
    var stack = exception.stack;
    if (!stack)
      return "";
    numIgnoredFrames = numIgnoredFrames || 0;
    if (stack.indexOf(exception.name) === 0)
      numIgnoredFrames += (exception.name + exception.message).split("\n").length;
    return stack.split("\n").slice(numIgnoredFrames).filter(libraryFilter).map((frame) => "\n" + frame).join("");
  }
  function DexieError(name, msg) {
    this._e = getErrorWithStack();
    this.name = name;
    this.message = msg;
  }
  function getMultiErrorMessage(msg, failures) {
    return msg + ". Errors: " + Object.keys(failures).map((key) => failures[key].toString()).filter((v, i, s) => s.indexOf(v) === i).join("\n");
  }
  function ModifyError(msg, failures, successCount, failedKeys) {
    this._e = getErrorWithStack();
    this.failures = failures;
    this.failedKeys = failedKeys;
    this.successCount = successCount;
    this.message = getMultiErrorMessage(msg, failures);
  }
  function BulkError(msg, failures) {
    this._e = getErrorWithStack();
    this.name = "BulkError";
    this.failures = Object.keys(failures).map((pos) => failures[pos]);
    this.failuresByPos = failures;
    this.message = getMultiErrorMessage(msg, failures);
  }
  function mapError(domError, message) {
    if (!domError || domError instanceof DexieError || domError instanceof TypeError || domError instanceof SyntaxError || !domError.name || !exceptionMap[domError.name])
      return domError;
    var rv = new exceptionMap[domError.name](message || domError.message, domError);
    if ("stack" in domError) {
      setProp(rv, "stack", { get: function() {
        return this.inner.stack;
      } });
    }
    return rv;
  }
  function nop() {
  }
  function mirror(val) {
    return val;
  }
  function pureFunctionChain(f1, f2) {
    if (f1 == null || f1 === mirror)
      return f2;
    return function(val) {
      return f2(f1(val));
    };
  }
  function callBoth(on1, on2) {
    return function() {
      on1.apply(this, arguments);
      on2.apply(this, arguments);
    };
  }
  function hookCreatingChain(f1, f2) {
    if (f1 === nop)
      return f2;
    return function() {
      var res = f1.apply(this, arguments);
      if (res !== void 0)
        arguments[0] = res;
      var onsuccess = this.onsuccess, onerror = this.onerror;
      this.onsuccess = null;
      this.onerror = null;
      var res2 = f2.apply(this, arguments);
      if (onsuccess)
        this.onsuccess = this.onsuccess ? callBoth(onsuccess, this.onsuccess) : onsuccess;
      if (onerror)
        this.onerror = this.onerror ? callBoth(onerror, this.onerror) : onerror;
      return res2 !== void 0 ? res2 : res;
    };
  }
  function hookDeletingChain(f1, f2) {
    if (f1 === nop)
      return f2;
    return function() {
      f1.apply(this, arguments);
      var onsuccess = this.onsuccess, onerror = this.onerror;
      this.onsuccess = this.onerror = null;
      f2.apply(this, arguments);
      if (onsuccess)
        this.onsuccess = this.onsuccess ? callBoth(onsuccess, this.onsuccess) : onsuccess;
      if (onerror)
        this.onerror = this.onerror ? callBoth(onerror, this.onerror) : onerror;
    };
  }
  function hookUpdatingChain(f1, f2) {
    if (f1 === nop)
      return f2;
    return function(modifications) {
      var res = f1.apply(this, arguments);
      extend(modifications, res);
      var onsuccess = this.onsuccess, onerror = this.onerror;
      this.onsuccess = null;
      this.onerror = null;
      var res2 = f2.apply(this, arguments);
      if (onsuccess)
        this.onsuccess = this.onsuccess ? callBoth(onsuccess, this.onsuccess) : onsuccess;
      if (onerror)
        this.onerror = this.onerror ? callBoth(onerror, this.onerror) : onerror;
      return res === void 0 ? res2 === void 0 ? void 0 : res2 : extend(res, res2);
    };
  }
  function reverseStoppableEventChain(f1, f2) {
    if (f1 === nop)
      return f2;
    return function() {
      if (f2.apply(this, arguments) === false)
        return false;
      return f1.apply(this, arguments);
    };
  }
  function promisableChain(f1, f2) {
    if (f1 === nop)
      return f2;
    return function() {
      var res = f1.apply(this, arguments);
      if (res && typeof res.then === "function") {
        var thiz = this, i = arguments.length, args = new Array(i);
        while (i--)
          args[i] = arguments[i];
        return res.then(function() {
          return f2.apply(thiz, args);
        });
      }
      return f2.apply(this, arguments);
    };
  }
  function DexiePromise(fn) {
    if (typeof this !== "object")
      throw new TypeError("Promises must be constructed via new");
    this._listeners = [];
    this.onuncatched = nop;
    this._lib = false;
    var psd = this._PSD = PSD;
    if (debug) {
      this._stackHolder = getErrorWithStack();
      this._prev = null;
      this._numPrev = 0;
    }
    if (typeof fn !== "function") {
      if (fn !== INTERNAL)
        throw new TypeError("Not a function");
      this._state = arguments[1];
      this._value = arguments[2];
      if (this._state === false)
        handleRejection(this, this._value);
      return;
    }
    this._state = null;
    this._value = null;
    ++psd.ref;
    executePromiseTask(this, fn);
  }
  function Listener(onFulfilled, onRejected, resolve, reject, zone) {
    this.onFulfilled = typeof onFulfilled === "function" ? onFulfilled : null;
    this.onRejected = typeof onRejected === "function" ? onRejected : null;
    this.resolve = resolve;
    this.reject = reject;
    this.psd = zone;
  }
  function executePromiseTask(promise, fn) {
    try {
      fn((value) => {
        if (promise._state !== null)
          return;
        if (value === promise)
          throw new TypeError("A promise cannot be resolved with itself.");
        var shouldExecuteTick = promise._lib && beginMicroTickScope();
        if (value && typeof value.then === "function") {
          executePromiseTask(promise, (resolve, reject) => {
            value instanceof DexiePromise ? value._then(resolve, reject) : value.then(resolve, reject);
          });
        } else {
          promise._state = true;
          promise._value = value;
          propagateAllListeners(promise);
        }
        if (shouldExecuteTick)
          endMicroTickScope();
      }, handleRejection.bind(null, promise));
    } catch (ex) {
      handleRejection(promise, ex);
    }
  }
  function handleRejection(promise, reason) {
    rejectingErrors.push(reason);
    if (promise._state !== null)
      return;
    var shouldExecuteTick = promise._lib && beginMicroTickScope();
    reason = rejectionMapper(reason);
    promise._state = false;
    promise._value = reason;
    debug && reason !== null && typeof reason === "object" && !reason._promise && tryCatch(() => {
      var origProp = getPropertyDescriptor(reason, "stack");
      reason._promise = promise;
      setProp(reason, "stack", {
        get: () => stack_being_generated ? origProp && (origProp.get ? origProp.get.apply(reason) : origProp.value) : promise.stack
      });
    });
    addPossiblyUnhandledError(promise);
    propagateAllListeners(promise);
    if (shouldExecuteTick)
      endMicroTickScope();
  }
  function propagateAllListeners(promise) {
    var listeners = promise._listeners;
    promise._listeners = [];
    for (var i = 0, len = listeners.length; i < len; ++i) {
      propagateToListener(promise, listeners[i]);
    }
    var psd = promise._PSD;
    --psd.ref || psd.finalize();
    if (numScheduledCalls === 0) {
      ++numScheduledCalls;
      asap(() => {
        if (--numScheduledCalls === 0)
          finalizePhysicalTick();
      }, []);
    }
  }
  function propagateToListener(promise, listener) {
    if (promise._state === null) {
      promise._listeners.push(listener);
      return;
    }
    var cb = promise._state ? listener.onFulfilled : listener.onRejected;
    if (cb === null) {
      return (promise._state ? listener.resolve : listener.reject)(promise._value);
    }
    ++listener.psd.ref;
    ++numScheduledCalls;
    asap(callListener, [cb, promise, listener]);
  }
  function callListener(cb, promise, listener) {
    try {
      currentFulfiller = promise;
      var ret, value = promise._value;
      if (promise._state) {
        ret = cb(value);
      } else {
        if (rejectingErrors.length)
          rejectingErrors = [];
        ret = cb(value);
        if (rejectingErrors.indexOf(value) === -1)
          markErrorAsHandled(promise);
      }
      listener.resolve(ret);
    } catch (e) {
      listener.reject(e);
    } finally {
      currentFulfiller = null;
      if (--numScheduledCalls === 0)
        finalizePhysicalTick();
      --listener.psd.ref || listener.psd.finalize();
    }
  }
  function getStack(promise, stacks, limit) {
    if (stacks.length === limit)
      return stacks;
    var stack = "";
    if (promise._state === false) {
      var failure = promise._value, errorName, message;
      if (failure != null) {
        errorName = failure.name || "Error";
        message = failure.message || failure;
        stack = prettyStack(failure, 0);
      } else {
        errorName = failure;
        message = "";
      }
      stacks.push(errorName + (message ? ": " + message : "") + stack);
    }
    if (debug) {
      stack = prettyStack(promise._stackHolder, 2);
      if (stack && stacks.indexOf(stack) === -1)
        stacks.push(stack);
      if (promise._prev)
        getStack(promise._prev, stacks, limit);
    }
    return stacks;
  }
  function linkToPreviousPromise(promise, prev) {
    var numPrev = prev ? prev._numPrev + 1 : 0;
    if (numPrev < LONG_STACKS_CLIP_LIMIT) {
      promise._prev = prev;
      promise._numPrev = numPrev;
    }
  }
  function physicalTick() {
    beginMicroTickScope() && endMicroTickScope();
  }
  function beginMicroTickScope() {
    var wasRootExec = isOutsideMicroTick;
    isOutsideMicroTick = false;
    needsNewPhysicalTick = false;
    return wasRootExec;
  }
  function endMicroTickScope() {
    var callbacks, i, l;
    do {
      while (microtickQueue.length > 0) {
        callbacks = microtickQueue;
        microtickQueue = [];
        l = callbacks.length;
        for (i = 0; i < l; ++i) {
          var item = callbacks[i];
          item[0].apply(null, item[1]);
        }
      }
    } while (microtickQueue.length > 0);
    isOutsideMicroTick = true;
    needsNewPhysicalTick = true;
  }
  function finalizePhysicalTick() {
    var unhandledErrs = unhandledErrors;
    unhandledErrors = [];
    unhandledErrs.forEach((p) => {
      p._PSD.onunhandled.call(null, p._value, p);
    });
    var finalizers = tickFinalizers.slice(0);
    var i = finalizers.length;
    while (i)
      finalizers[--i]();
  }
  function run_at_end_of_this_or_next_physical_tick(fn) {
    function finalizer() {
      fn();
      tickFinalizers.splice(tickFinalizers.indexOf(finalizer), 1);
    }
    tickFinalizers.push(finalizer);
    ++numScheduledCalls;
    asap(() => {
      if (--numScheduledCalls === 0)
        finalizePhysicalTick();
    }, []);
  }
  function addPossiblyUnhandledError(promise) {
    if (!unhandledErrors.some((p) => p._value === promise._value))
      unhandledErrors.push(promise);
  }
  function markErrorAsHandled(promise) {
    var i = unhandledErrors.length;
    while (i)
      if (unhandledErrors[--i]._value === promise._value) {
        unhandledErrors.splice(i, 1);
        return;
      }
  }
  function PromiseReject(reason) {
    return new DexiePromise(INTERNAL, false, reason);
  }
  function wrap(fn, errorCatcher) {
    var psd = PSD;
    return function() {
      var wasRootExec = beginMicroTickScope(), outerScope = PSD;
      try {
        switchToZone(psd, true);
        return fn.apply(this, arguments);
      } catch (e) {
        errorCatcher && errorCatcher(e);
      } finally {
        switchToZone(outerScope, false);
        if (wasRootExec)
          endMicroTickScope();
      }
    };
  }
  function newScope(fn, props2, a1, a2) {
    var parent = PSD, psd = Object.create(parent);
    psd.parent = parent;
    psd.ref = 0;
    psd.global = false;
    psd.id = ++zone_id_counter;
    var globalEnv = globalPSD.env;
    psd.env = patchGlobalPromise ? {
      Promise: DexiePromise,
      PromiseProp: { value: DexiePromise, configurable: true, writable: true },
      all: DexiePromise.all,
      race: DexiePromise.race,
      allSettled: DexiePromise.allSettled,
      any: DexiePromise.any,
      resolve: DexiePromise.resolve,
      reject: DexiePromise.reject,
      nthen: getPatchedPromiseThen(globalEnv.nthen, psd),
      gthen: getPatchedPromiseThen(globalEnv.gthen, psd)
    } : {};
    if (props2)
      extend(psd, props2);
    ++parent.ref;
    psd.finalize = function() {
      --this.parent.ref || this.parent.finalize();
    };
    var rv = usePSD(psd, fn, a1, a2);
    if (psd.ref === 0)
      psd.finalize();
    return rv;
  }
  function incrementExpectedAwaits() {
    if (!task.id)
      task.id = ++taskCounter;
    ++task.awaits;
    task.echoes += ZONE_ECHO_LIMIT;
    return task.id;
  }
  function decrementExpectedAwaits() {
    if (!task.awaits)
      return false;
    if (--task.awaits === 0)
      task.id = 0;
    task.echoes = task.awaits * ZONE_ECHO_LIMIT;
    return true;
  }
  function onPossibleParallellAsync(possiblePromise) {
    if (task.echoes && possiblePromise && possiblePromise.constructor === NativePromise) {
      incrementExpectedAwaits();
      return possiblePromise.then((x) => {
        decrementExpectedAwaits();
        return x;
      }, (e) => {
        decrementExpectedAwaits();
        return rejection(e);
      });
    }
    return possiblePromise;
  }
  function zoneEnterEcho(targetZone) {
    ++totalEchoes;
    if (!task.echoes || --task.echoes === 0) {
      task.echoes = task.id = 0;
    }
    zoneStack.push(PSD);
    switchToZone(targetZone, true);
  }
  function zoneLeaveEcho() {
    var zone = zoneStack[zoneStack.length - 1];
    zoneStack.pop();
    switchToZone(zone, false);
  }
  function switchToZone(targetZone, bEnteringZone) {
    var currentZone = PSD;
    if (bEnteringZone ? task.echoes && (!zoneEchoes++ || targetZone !== PSD) : zoneEchoes && (!--zoneEchoes || targetZone !== PSD)) {
      enqueueNativeMicroTask(bEnteringZone ? zoneEnterEcho.bind(null, targetZone) : zoneLeaveEcho);
    }
    if (targetZone === PSD)
      return;
    PSD = targetZone;
    if (currentZone === globalPSD)
      globalPSD.env = snapShot();
    if (patchGlobalPromise) {
      var GlobalPromise = globalPSD.env.Promise;
      var targetEnv = targetZone.env;
      nativePromiseProto.then = targetEnv.nthen;
      GlobalPromise.prototype.then = targetEnv.gthen;
      if (currentZone.global || targetZone.global) {
        Object.defineProperty(_global, "Promise", targetEnv.PromiseProp);
        GlobalPromise.all = targetEnv.all;
        GlobalPromise.race = targetEnv.race;
        GlobalPromise.resolve = targetEnv.resolve;
        GlobalPromise.reject = targetEnv.reject;
        if (targetEnv.allSettled)
          GlobalPromise.allSettled = targetEnv.allSettled;
        if (targetEnv.any)
          GlobalPromise.any = targetEnv.any;
      }
    }
  }
  function snapShot() {
    var GlobalPromise = _global.Promise;
    return patchGlobalPromise ? {
      Promise: GlobalPromise,
      PromiseProp: Object.getOwnPropertyDescriptor(_global, "Promise"),
      all: GlobalPromise.all,
      race: GlobalPromise.race,
      allSettled: GlobalPromise.allSettled,
      any: GlobalPromise.any,
      resolve: GlobalPromise.resolve,
      reject: GlobalPromise.reject,
      nthen: nativePromiseProto.then,
      gthen: GlobalPromise.prototype.then
    } : {};
  }
  function usePSD(psd, fn, a1, a2, a3) {
    var outerScope = PSD;
    try {
      switchToZone(psd, true);
      return fn(a1, a2, a3);
    } finally {
      switchToZone(outerScope, false);
    }
  }
  function enqueueNativeMicroTask(job) {
    nativePromiseThen.call(resolvedNativePromise, job);
  }
  function nativeAwaitCompatibleWrap(fn, zone, possibleAwait, cleanup) {
    return typeof fn !== "function" ? fn : function() {
      var outerZone = PSD;
      if (possibleAwait)
        incrementExpectedAwaits();
      switchToZone(zone, true);
      try {
        return fn.apply(this, arguments);
      } finally {
        switchToZone(outerZone, false);
        if (cleanup)
          enqueueNativeMicroTask(decrementExpectedAwaits);
      }
    };
  }
  function getPatchedPromiseThen(origThen, zone) {
    return function(onResolved, onRejected) {
      return origThen.call(this, nativeAwaitCompatibleWrap(onResolved, zone), nativeAwaitCompatibleWrap(onRejected, zone));
    };
  }
  function globalError(err, promise) {
    var rv;
    try {
      rv = promise.onuncatched(err);
    } catch (e) {
    }
    if (rv !== false)
      try {
        var event, eventData = { promise, reason: err };
        if (_global.document && document.createEvent) {
          event = document.createEvent("Event");
          event.initEvent(UNHANDLEDREJECTION, true, true);
          extend(event, eventData);
        } else if (_global.CustomEvent) {
          event = new CustomEvent(UNHANDLEDREJECTION, { detail: eventData });
          extend(event, eventData);
        }
        if (event && _global.dispatchEvent) {
          dispatchEvent(event);
          if (!_global.PromiseRejectionEvent && _global.onunhandledrejection)
            try {
              _global.onunhandledrejection(event);
            } catch (_) {
            }
        }
        if (debug && event && !event.defaultPrevented) {
          console.warn(`Unhandled rejection: ${err.stack || err}`);
        }
      } catch (e) {
      }
  }
  function tempTransaction(db, mode, storeNames, fn) {
    if (!db.idbdb || !db._state.openComplete && (!PSD.letThrough && !db._vip)) {
      if (db._state.openComplete) {
        return rejection(new exceptions.DatabaseClosed(db._state.dbOpenError));
      }
      if (!db._state.isBeingOpened) {
        if (!db._options.autoOpen)
          return rejection(new exceptions.DatabaseClosed());
        db.open().catch(nop);
      }
      return db._state.dbReadyPromise.then(() => tempTransaction(db, mode, storeNames, fn));
    } else {
      var trans = db._createTransaction(mode, storeNames, db._dbSchema);
      try {
        trans.create();
        db._state.PR1398_maxLoop = 3;
      } catch (ex) {
        if (ex.name === errnames.InvalidState && db.isOpen() && --db._state.PR1398_maxLoop > 0) {
          console.warn("Dexie: Need to reopen db");
          db._close();
          return db.open().then(() => tempTransaction(db, mode, storeNames, fn));
        }
        return rejection(ex);
      }
      return trans._promise(mode, (resolve, reject) => {
        return newScope(() => {
          PSD.trans = trans;
          return fn(resolve, reject, trans);
        });
      }).then((result) => {
        return trans._completion.then(() => result);
      });
    }
  }
  function combine(filter1, filter2) {
    return filter1 ? filter2 ? function() {
      return filter1.apply(this, arguments) && filter2.apply(this, arguments);
    } : filter1 : filter2;
  }
  function workaroundForUndefinedPrimKey(keyPath) {
    return typeof keyPath === "string" && !/\./.test(keyPath) ? (obj) => {
      if (obj[keyPath] === void 0 && keyPath in obj) {
        obj = deepClone(obj);
        delete obj[keyPath];
      }
      return obj;
    } : (obj) => obj;
  }
  function Events(ctx) {
    var evs = {};
    var rv = function(eventName, subscriber) {
      if (subscriber) {
        var i2 = arguments.length, args = new Array(i2 - 1);
        while (--i2)
          args[i2 - 1] = arguments[i2];
        evs[eventName].subscribe.apply(null, args);
        return ctx;
      } else if (typeof eventName === "string") {
        return evs[eventName];
      }
    };
    rv.addEventType = add;
    for (var i = 1, l = arguments.length; i < l; ++i) {
      add(arguments[i]);
    }
    return rv;
    function add(eventName, chainFunction, defaultFunction) {
      if (typeof eventName === "object")
        return addConfiguredEvents(eventName);
      if (!chainFunction)
        chainFunction = reverseStoppableEventChain;
      if (!defaultFunction)
        defaultFunction = nop;
      var context = {
        subscribers: [],
        fire: defaultFunction,
        subscribe: function(cb) {
          if (context.subscribers.indexOf(cb) === -1) {
            context.subscribers.push(cb);
            context.fire = chainFunction(context.fire, cb);
          }
        },
        unsubscribe: function(cb) {
          context.subscribers = context.subscribers.filter(function(fn) {
            return fn !== cb;
          });
          context.fire = context.subscribers.reduce(chainFunction, defaultFunction);
        }
      };
      evs[eventName] = rv[eventName] = context;
      return context;
    }
    function addConfiguredEvents(cfg) {
      keys(cfg).forEach(function(eventName) {
        var args = cfg[eventName];
        if (isArray(args)) {
          add(eventName, cfg[eventName][0], cfg[eventName][1]);
        } else if (args === "asap") {
          var context = add(eventName, mirror, function fire() {
            var i2 = arguments.length, args2 = new Array(i2);
            while (i2--)
              args2[i2] = arguments[i2];
            context.subscribers.forEach(function(fn) {
              asap$1(function fireEvent() {
                fn.apply(null, args2);
              });
            });
          });
        } else
          throw new exceptions.InvalidArgument("Invalid event config");
      });
    }
  }
  function makeClassConstructor(prototype, constructor) {
    derive(constructor).from({ prototype });
    return constructor;
  }
  function createTableConstructor(db) {
    return makeClassConstructor(Table.prototype, function Table2(name, tableSchema, trans) {
      this.db = db;
      this._tx = trans;
      this.name = name;
      this.schema = tableSchema;
      this.hook = db._allTables[name] ? db._allTables[name].hook : Events(null, {
        "creating": [hookCreatingChain, nop],
        "reading": [pureFunctionChain, mirror],
        "updating": [hookUpdatingChain, nop],
        "deleting": [hookDeletingChain, nop]
      });
    });
  }
  function isPlainKeyRange(ctx, ignoreLimitFilter) {
    return !(ctx.filter || ctx.algorithm || ctx.or) && (ignoreLimitFilter ? ctx.justLimit : !ctx.replayFilter);
  }
  function addFilter(ctx, fn) {
    ctx.filter = combine(ctx.filter, fn);
  }
  function addReplayFilter(ctx, factory, isLimitFilter) {
    var curr = ctx.replayFilter;
    ctx.replayFilter = curr ? () => combine(curr(), factory()) : factory;
    ctx.justLimit = isLimitFilter && !curr;
  }
  function addMatchFilter(ctx, fn) {
    ctx.isMatch = combine(ctx.isMatch, fn);
  }
  function getIndexOrStore(ctx, coreSchema) {
    if (ctx.isPrimKey)
      return coreSchema.primaryKey;
    const index = coreSchema.getIndexByKeyPath(ctx.index);
    if (!index)
      throw new exceptions.Schema("KeyPath " + ctx.index + " on object store " + coreSchema.name + " is not indexed");
    return index;
  }
  function openCursor(ctx, coreTable, trans) {
    const index = getIndexOrStore(ctx, coreTable.schema);
    return coreTable.openCursor({
      trans,
      values: !ctx.keysOnly,
      reverse: ctx.dir === "prev",
      unique: !!ctx.unique,
      query: {
        index,
        range: ctx.range
      }
    });
  }
  function iter(ctx, fn, coreTrans, coreTable) {
    const filter = ctx.replayFilter ? combine(ctx.filter, ctx.replayFilter()) : ctx.filter;
    if (!ctx.or) {
      return iterate(openCursor(ctx, coreTable, coreTrans), combine(ctx.algorithm, filter), fn, !ctx.keysOnly && ctx.valueMapper);
    } else {
      const set = {};
      const union = (item, cursor, advance) => {
        if (!filter || filter(cursor, advance, (result) => cursor.stop(result), (err) => cursor.fail(err))) {
          var primaryKey = cursor.primaryKey;
          var key = "" + primaryKey;
          if (key === "[object ArrayBuffer]")
            key = "" + new Uint8Array(primaryKey);
          if (!hasOwn(set, key)) {
            set[key] = true;
            fn(item, cursor, advance);
          }
        }
      };
      return Promise.all([
        ctx.or._iterate(union, coreTrans),
        iterate(openCursor(ctx, coreTable, coreTrans), ctx.algorithm, union, !ctx.keysOnly && ctx.valueMapper)
      ]);
    }
  }
  function iterate(cursorPromise, filter, fn, valueMapper) {
    var mappedFn = valueMapper ? (x, c, a) => fn(valueMapper(x), c, a) : fn;
    var wrappedFn = wrap(mappedFn);
    return cursorPromise.then((cursor) => {
      if (cursor) {
        return cursor.start(() => {
          var c = () => cursor.continue();
          if (!filter || filter(cursor, (advancer) => c = advancer, (val) => {
            cursor.stop(val);
            c = nop;
          }, (e) => {
            cursor.fail(e);
            c = nop;
          }))
            wrappedFn(cursor.value, cursor, (advancer) => c = advancer);
          c();
        });
      }
    });
  }
  function cmp(a, b) {
    try {
      const ta = type(a);
      const tb = type(b);
      if (ta !== tb) {
        if (ta === "Array")
          return 1;
        if (tb === "Array")
          return -1;
        if (ta === "binary")
          return 1;
        if (tb === "binary")
          return -1;
        if (ta === "string")
          return 1;
        if (tb === "string")
          return -1;
        if (ta === "Date")
          return 1;
        if (tb !== "Date")
          return NaN;
        return -1;
      }
      switch (ta) {
        case "number":
        case "Date":
        case "string":
          return a > b ? 1 : a < b ? -1 : 0;
        case "binary": {
          return compareUint8Arrays(getUint8Array(a), getUint8Array(b));
        }
        case "Array":
          return compareArrays(a, b);
      }
    } catch (_a) {
    }
    return NaN;
  }
  function compareArrays(a, b) {
    const al = a.length;
    const bl = b.length;
    const l = al < bl ? al : bl;
    for (let i = 0; i < l; ++i) {
      const res = cmp(a[i], b[i]);
      if (res !== 0)
        return res;
    }
    return al === bl ? 0 : al < bl ? -1 : 1;
  }
  function compareUint8Arrays(a, b) {
    const al = a.length;
    const bl = b.length;
    const l = al < bl ? al : bl;
    for (let i = 0; i < l; ++i) {
      if (a[i] !== b[i])
        return a[i] < b[i] ? -1 : 1;
    }
    return al === bl ? 0 : al < bl ? -1 : 1;
  }
  function type(x) {
    const t = typeof x;
    if (t !== "object")
      return t;
    if (ArrayBuffer.isView(x))
      return "binary";
    const tsTag = toStringTag(x);
    return tsTag === "ArrayBuffer" ? "binary" : tsTag;
  }
  function getUint8Array(a) {
    if (a instanceof Uint8Array)
      return a;
    if (ArrayBuffer.isView(a))
      return new Uint8Array(a.buffer, a.byteOffset, a.byteLength);
    return new Uint8Array(a);
  }
  function createCollectionConstructor(db) {
    return makeClassConstructor(Collection.prototype, function Collection2(whereClause, keyRangeGenerator) {
      this.db = db;
      let keyRange = AnyRange, error = null;
      if (keyRangeGenerator)
        try {
          keyRange = keyRangeGenerator();
        } catch (ex) {
          error = ex;
        }
      const whereCtx = whereClause._ctx;
      const table = whereCtx.table;
      const readingHook = table.hook.reading.fire;
      this._ctx = {
        table,
        index: whereCtx.index,
        isPrimKey: !whereCtx.index || table.schema.primKey.keyPath && whereCtx.index === table.schema.primKey.name,
        range: keyRange,
        keysOnly: false,
        dir: "next",
        unique: "",
        algorithm: null,
        filter: null,
        replayFilter: null,
        justLimit: true,
        isMatch: null,
        offset: 0,
        limit: Infinity,
        error,
        or: whereCtx.or,
        valueMapper: readingHook !== mirror ? readingHook : null
      };
    });
  }
  function simpleCompare(a, b) {
    return a < b ? -1 : a === b ? 0 : 1;
  }
  function simpleCompareReverse(a, b) {
    return a > b ? -1 : a === b ? 0 : 1;
  }
  function fail(collectionOrWhereClause, err, T) {
    var collection = collectionOrWhereClause instanceof WhereClause ? new collectionOrWhereClause.Collection(collectionOrWhereClause) : collectionOrWhereClause;
    collection._ctx.error = T ? new T(err) : new TypeError(err);
    return collection;
  }
  function emptyCollection(whereClause) {
    return new whereClause.Collection(whereClause, () => rangeEqual("")).limit(0);
  }
  function upperFactory(dir) {
    return dir === "next" ? (s) => s.toUpperCase() : (s) => s.toLowerCase();
  }
  function lowerFactory(dir) {
    return dir === "next" ? (s) => s.toLowerCase() : (s) => s.toUpperCase();
  }
  function nextCasing(key, lowerKey, upperNeedle, lowerNeedle, cmp2, dir) {
    var length = Math.min(key.length, lowerNeedle.length);
    var llp = -1;
    for (var i = 0; i < length; ++i) {
      var lwrKeyChar = lowerKey[i];
      if (lwrKeyChar !== lowerNeedle[i]) {
        if (cmp2(key[i], upperNeedle[i]) < 0)
          return key.substr(0, i) + upperNeedle[i] + upperNeedle.substr(i + 1);
        if (cmp2(key[i], lowerNeedle[i]) < 0)
          return key.substr(0, i) + lowerNeedle[i] + upperNeedle.substr(i + 1);
        if (llp >= 0)
          return key.substr(0, llp) + lowerKey[llp] + upperNeedle.substr(llp + 1);
        return null;
      }
      if (cmp2(key[i], lwrKeyChar) < 0)
        llp = i;
    }
    if (length < lowerNeedle.length && dir === "next")
      return key + upperNeedle.substr(key.length);
    if (length < key.length && dir === "prev")
      return key.substr(0, upperNeedle.length);
    return llp < 0 ? null : key.substr(0, llp) + lowerNeedle[llp] + upperNeedle.substr(llp + 1);
  }
  function addIgnoreCaseAlgorithm(whereClause, match, needles, suffix) {
    var upper, lower, compare, upperNeedles, lowerNeedles, direction, nextKeySuffix, needlesLen = needles.length;
    if (!needles.every((s) => typeof s === "string")) {
      return fail(whereClause, STRING_EXPECTED);
    }
    function initDirection(dir) {
      upper = upperFactory(dir);
      lower = lowerFactory(dir);
      compare = dir === "next" ? simpleCompare : simpleCompareReverse;
      var needleBounds = needles.map(function(needle) {
        return { lower: lower(needle), upper: upper(needle) };
      }).sort(function(a, b) {
        return compare(a.lower, b.lower);
      });
      upperNeedles = needleBounds.map(function(nb) {
        return nb.upper;
      });
      lowerNeedles = needleBounds.map(function(nb) {
        return nb.lower;
      });
      direction = dir;
      nextKeySuffix = dir === "next" ? "" : suffix;
    }
    initDirection("next");
    var c = new whereClause.Collection(whereClause, () => createRange(upperNeedles[0], lowerNeedles[needlesLen - 1] + suffix));
    c._ondirectionchange = function(direction2) {
      initDirection(direction2);
    };
    var firstPossibleNeedle = 0;
    c._addAlgorithm(function(cursor, advance, resolve) {
      var key = cursor.key;
      if (typeof key !== "string")
        return false;
      var lowerKey = lower(key);
      if (match(lowerKey, lowerNeedles, firstPossibleNeedle)) {
        return true;
      } else {
        var lowestPossibleCasing = null;
        for (var i = firstPossibleNeedle; i < needlesLen; ++i) {
          var casing = nextCasing(key, lowerKey, upperNeedles[i], lowerNeedles[i], compare, direction);
          if (casing === null && lowestPossibleCasing === null)
            firstPossibleNeedle = i + 1;
          else if (lowestPossibleCasing === null || compare(lowestPossibleCasing, casing) > 0) {
            lowestPossibleCasing = casing;
          }
        }
        if (lowestPossibleCasing !== null) {
          advance(function() {
            cursor.continue(lowestPossibleCasing + nextKeySuffix);
          });
        } else {
          advance(resolve);
        }
        return false;
      }
    });
    return c;
  }
  function createRange(lower, upper, lowerOpen, upperOpen) {
    return {
      type: 2,
      lower,
      upper,
      lowerOpen,
      upperOpen
    };
  }
  function rangeEqual(value) {
    return {
      type: 1,
      lower: value,
      upper: value
    };
  }
  function createWhereClauseConstructor(db) {
    return makeClassConstructor(WhereClause.prototype, function WhereClause2(table, index, orCollection) {
      this.db = db;
      this._ctx = {
        table,
        index: index === ":id" ? null : index,
        or: orCollection
      };
      const indexedDB2 = db._deps.indexedDB;
      if (!indexedDB2)
        throw new exceptions.MissingAPI();
      this._cmp = this._ascending = indexedDB2.cmp.bind(indexedDB2);
      this._descending = (a, b) => indexedDB2.cmp(b, a);
      this._max = (a, b) => indexedDB2.cmp(a, b) > 0 ? a : b;
      this._min = (a, b) => indexedDB2.cmp(a, b) < 0 ? a : b;
      this._IDBKeyRange = db._deps.IDBKeyRange;
    });
  }
  function eventRejectHandler(reject) {
    return wrap(function(event) {
      preventDefault(event);
      reject(event.target.error);
      return false;
    });
  }
  function preventDefault(event) {
    if (event.stopPropagation)
      event.stopPropagation();
    if (event.preventDefault)
      event.preventDefault();
  }
  function createTransactionConstructor(db) {
    return makeClassConstructor(Transaction.prototype, function Transaction2(mode, storeNames, dbschema, chromeTransactionDurability, parent) {
      this.db = db;
      this.mode = mode;
      this.storeNames = storeNames;
      this.schema = dbschema;
      this.chromeTransactionDurability = chromeTransactionDurability;
      this.idbtrans = null;
      this.on = Events(this, "complete", "error", "abort");
      this.parent = parent || null;
      this.active = true;
      this._reculock = 0;
      this._blockedFuncs = [];
      this._resolve = null;
      this._reject = null;
      this._waitingFor = null;
      this._waitingQueue = null;
      this._spinCount = 0;
      this._completion = new DexiePromise((resolve, reject) => {
        this._resolve = resolve;
        this._reject = reject;
      });
      this._completion.then(() => {
        this.active = false;
        this.on.complete.fire();
      }, (e) => {
        var wasActive = this.active;
        this.active = false;
        this.on.error.fire(e);
        this.parent ? this.parent._reject(e) : wasActive && this.idbtrans && this.idbtrans.abort();
        return rejection(e);
      });
    });
  }
  function createIndexSpec(name, keyPath, unique, multi, auto, compound, isPrimKey) {
    return {
      name,
      keyPath,
      unique,
      multi,
      auto,
      compound,
      src: (unique && !isPrimKey ? "&" : "") + (multi ? "*" : "") + (auto ? "++" : "") + nameFromKeyPath(keyPath)
    };
  }
  function nameFromKeyPath(keyPath) {
    return typeof keyPath === "string" ? keyPath : keyPath ? "[" + [].join.call(keyPath, "+") + "]" : "";
  }
  function createTableSchema(name, primKey, indexes) {
    return {
      name,
      primKey,
      indexes,
      mappedClass: null,
      idxByName: arrayToObject(indexes, (index) => [index.name, index])
    };
  }
  function safariMultiStoreFix(storeNames) {
    return storeNames.length === 1 ? storeNames[0] : storeNames;
  }
  function getKeyExtractor(keyPath) {
    if (keyPath == null) {
      return () => void 0;
    } else if (typeof keyPath === "string") {
      return getSinglePathKeyExtractor(keyPath);
    } else {
      return (obj) => getByKeyPath(obj, keyPath);
    }
  }
  function getSinglePathKeyExtractor(keyPath) {
    const split = keyPath.split(".");
    if (split.length === 1) {
      return (obj) => obj[keyPath];
    } else {
      return (obj) => getByKeyPath(obj, keyPath);
    }
  }
  function arrayify(arrayLike) {
    return [].slice.call(arrayLike);
  }
  function getKeyPathAlias(keyPath) {
    return keyPath == null ? ":id" : typeof keyPath === "string" ? keyPath : `[${keyPath.join("+")}]`;
  }
  function createDBCore(db, IdbKeyRange, tmpTrans) {
    function extractSchema(db2, trans) {
      const tables2 = arrayify(db2.objectStoreNames);
      return {
        schema: {
          name: db2.name,
          tables: tables2.map((table) => trans.objectStore(table)).map((store) => {
            const { keyPath, autoIncrement } = store;
            const compound = isArray(keyPath);
            const outbound = keyPath == null;
            const indexByKeyPath = {};
            const result = {
              name: store.name,
              primaryKey: {
                name: null,
                isPrimaryKey: true,
                outbound,
                compound,
                keyPath,
                autoIncrement,
                unique: true,
                extractKey: getKeyExtractor(keyPath)
              },
              indexes: arrayify(store.indexNames).map((indexName) => store.index(indexName)).map((index) => {
                const { name, unique, multiEntry, keyPath: keyPath2 } = index;
                const compound2 = isArray(keyPath2);
                const result2 = {
                  name,
                  compound: compound2,
                  keyPath: keyPath2,
                  unique,
                  multiEntry,
                  extractKey: getKeyExtractor(keyPath2)
                };
                indexByKeyPath[getKeyPathAlias(keyPath2)] = result2;
                return result2;
              }),
              getIndexByKeyPath: (keyPath2) => indexByKeyPath[getKeyPathAlias(keyPath2)]
            };
            indexByKeyPath[":id"] = result.primaryKey;
            if (keyPath != null) {
              indexByKeyPath[getKeyPathAlias(keyPath)] = result.primaryKey;
            }
            return result;
          })
        },
        hasGetAll: tables2.length > 0 && "getAll" in trans.objectStore(tables2[0]) && !(typeof navigator !== "undefined" && /Safari/.test(navigator.userAgent) && !/(Chrome\/|Edge\/)/.test(navigator.userAgent) && [].concat(navigator.userAgent.match(/Safari\/(\d*)/))[1] < 604)
      };
    }
    function makeIDBKeyRange(range) {
      if (range.type === 3)
        return null;
      if (range.type === 4)
        throw new Error("Cannot convert never type to IDBKeyRange");
      const { lower, upper, lowerOpen, upperOpen } = range;
      const idbRange = lower === void 0 ? upper === void 0 ? null : IdbKeyRange.upperBound(upper, !!upperOpen) : upper === void 0 ? IdbKeyRange.lowerBound(lower, !!lowerOpen) : IdbKeyRange.bound(lower, upper, !!lowerOpen, !!upperOpen);
      return idbRange;
    }
    function createDbCoreTable(tableSchema) {
      const tableName = tableSchema.name;
      function mutate({ trans, type: type2, keys: keys2, values, range }) {
        return new Promise((resolve, reject) => {
          resolve = wrap(resolve);
          const store = trans.objectStore(tableName);
          const outbound = store.keyPath == null;
          const isAddOrPut = type2 === "put" || type2 === "add";
          if (!isAddOrPut && type2 !== "delete" && type2 !== "deleteRange")
            throw new Error("Invalid operation type: " + type2);
          const { length } = keys2 || values || { length: 1 };
          if (keys2 && values && keys2.length !== values.length) {
            throw new Error("Given keys array must have same length as given values array.");
          }
          if (length === 0)
            return resolve({ numFailures: 0, failures: {}, results: [], lastResult: void 0 });
          let req;
          const reqs = [];
          const failures = [];
          let numFailures = 0;
          const errorHandler = (event) => {
            ++numFailures;
            preventDefault(event);
          };
          if (type2 === "deleteRange") {
            if (range.type === 4)
              return resolve({ numFailures, failures, results: [], lastResult: void 0 });
            if (range.type === 3)
              reqs.push(req = store.clear());
            else
              reqs.push(req = store.delete(makeIDBKeyRange(range)));
          } else {
            const [args1, args2] = isAddOrPut ? outbound ? [values, keys2] : [values, null] : [keys2, null];
            if (isAddOrPut) {
              for (let i = 0; i < length; ++i) {
                reqs.push(req = args2 && args2[i] !== void 0 ? store[type2](args1[i], args2[i]) : store[type2](args1[i]));
                req.onerror = errorHandler;
              }
            } else {
              for (let i = 0; i < length; ++i) {
                reqs.push(req = store[type2](args1[i]));
                req.onerror = errorHandler;
              }
            }
          }
          const done = (event) => {
            const lastResult = event.target.result;
            reqs.forEach((req2, i) => req2.error != null && (failures[i] = req2.error));
            resolve({
              numFailures,
              failures,
              results: type2 === "delete" ? keys2 : reqs.map((req2) => req2.result),
              lastResult
            });
          };
          req.onerror = (event) => {
            errorHandler(event);
            done(event);
          };
          req.onsuccess = done;
        });
      }
      function openCursor2({ trans, values, query: query2, reverse, unique }) {
        return new Promise((resolve, reject) => {
          resolve = wrap(resolve);
          const { index, range } = query2;
          const store = trans.objectStore(tableName);
          const source = index.isPrimaryKey ? store : store.index(index.name);
          const direction = reverse ? unique ? "prevunique" : "prev" : unique ? "nextunique" : "next";
          const req = values || !("openKeyCursor" in source) ? source.openCursor(makeIDBKeyRange(range), direction) : source.openKeyCursor(makeIDBKeyRange(range), direction);
          req.onerror = eventRejectHandler(reject);
          req.onsuccess = wrap((ev) => {
            const cursor = req.result;
            if (!cursor) {
              resolve(null);
              return;
            }
            cursor.___id = ++_id_counter;
            cursor.done = false;
            const _cursorContinue = cursor.continue.bind(cursor);
            let _cursorContinuePrimaryKey = cursor.continuePrimaryKey;
            if (_cursorContinuePrimaryKey)
              _cursorContinuePrimaryKey = _cursorContinuePrimaryKey.bind(cursor);
            const _cursorAdvance = cursor.advance.bind(cursor);
            const doThrowCursorIsNotStarted = () => {
              throw new Error("Cursor not started");
            };
            const doThrowCursorIsStopped = () => {
              throw new Error("Cursor not stopped");
            };
            cursor.trans = trans;
            cursor.stop = cursor.continue = cursor.continuePrimaryKey = cursor.advance = doThrowCursorIsNotStarted;
            cursor.fail = wrap(reject);
            cursor.next = function() {
              let gotOne = 1;
              return this.start(() => gotOne-- ? this.continue() : this.stop()).then(() => this);
            };
            cursor.start = (callback) => {
              const iterationPromise = new Promise((resolveIteration, rejectIteration) => {
                resolveIteration = wrap(resolveIteration);
                req.onerror = eventRejectHandler(rejectIteration);
                cursor.fail = rejectIteration;
                cursor.stop = (value) => {
                  cursor.stop = cursor.continue = cursor.continuePrimaryKey = cursor.advance = doThrowCursorIsStopped;
                  resolveIteration(value);
                };
              });
              const guardedCallback = () => {
                if (req.result) {
                  try {
                    callback();
                  } catch (err) {
                    cursor.fail(err);
                  }
                } else {
                  cursor.done = true;
                  cursor.start = () => {
                    throw new Error("Cursor behind last entry");
                  };
                  cursor.stop();
                }
              };
              req.onsuccess = wrap((ev2) => {
                req.onsuccess = guardedCallback;
                guardedCallback();
              });
              cursor.continue = _cursorContinue;
              cursor.continuePrimaryKey = _cursorContinuePrimaryKey;
              cursor.advance = _cursorAdvance;
              guardedCallback();
              return iterationPromise;
            };
            resolve(cursor);
          }, reject);
        });
      }
      function query(hasGetAll2) {
        return (request) => {
          return new Promise((resolve, reject) => {
            resolve = wrap(resolve);
            const { trans, values, limit, query: query2 } = request;
            const nonInfinitLimit = limit === Infinity ? void 0 : limit;
            const { index, range } = query2;
            const store = trans.objectStore(tableName);
            const source = index.isPrimaryKey ? store : store.index(index.name);
            const idbKeyRange = makeIDBKeyRange(range);
            if (limit === 0)
              return resolve({ result: [] });
            if (hasGetAll2) {
              const req = values ? source.getAll(idbKeyRange, nonInfinitLimit) : source.getAllKeys(idbKeyRange, nonInfinitLimit);
              req.onsuccess = (event) => resolve({ result: event.target.result });
              req.onerror = eventRejectHandler(reject);
            } else {
              let count = 0;
              const req = values || !("openKeyCursor" in source) ? source.openCursor(idbKeyRange) : source.openKeyCursor(idbKeyRange);
              const result = [];
              req.onsuccess = (event) => {
                const cursor = req.result;
                if (!cursor)
                  return resolve({ result });
                result.push(values ? cursor.value : cursor.primaryKey);
                if (++count === limit)
                  return resolve({ result });
                cursor.continue();
              };
              req.onerror = eventRejectHandler(reject);
            }
          });
        };
      }
      return {
        name: tableName,
        schema: tableSchema,
        mutate,
        getMany({ trans, keys: keys2 }) {
          return new Promise((resolve, reject) => {
            resolve = wrap(resolve);
            const store = trans.objectStore(tableName);
            const length = keys2.length;
            const result = new Array(length);
            let keyCount = 0;
            let callbackCount = 0;
            let req;
            const successHandler = (event) => {
              const req2 = event.target;
              if ((result[req2._pos] = req2.result) != null)
                ;
              if (++callbackCount === keyCount)
                resolve(result);
            };
            const errorHandler = eventRejectHandler(reject);
            for (let i = 0; i < length; ++i) {
              const key = keys2[i];
              if (key != null) {
                req = store.get(keys2[i]);
                req._pos = i;
                req.onsuccess = successHandler;
                req.onerror = errorHandler;
                ++keyCount;
              }
            }
            if (keyCount === 0)
              resolve(result);
          });
        },
        get({ trans, key }) {
          return new Promise((resolve, reject) => {
            resolve = wrap(resolve);
            const store = trans.objectStore(tableName);
            const req = store.get(key);
            req.onsuccess = (event) => resolve(event.target.result);
            req.onerror = eventRejectHandler(reject);
          });
        },
        query: query(hasGetAll),
        openCursor: openCursor2,
        count({ query: query2, trans }) {
          const { index, range } = query2;
          return new Promise((resolve, reject) => {
            const store = trans.objectStore(tableName);
            const source = index.isPrimaryKey ? store : store.index(index.name);
            const idbKeyRange = makeIDBKeyRange(range);
            const req = idbKeyRange ? source.count(idbKeyRange) : source.count();
            req.onsuccess = wrap((ev) => resolve(ev.target.result));
            req.onerror = eventRejectHandler(reject);
          });
        }
      };
    }
    const { schema, hasGetAll } = extractSchema(db, tmpTrans);
    const tables = schema.tables.map((tableSchema) => createDbCoreTable(tableSchema));
    const tableMap = {};
    tables.forEach((table) => tableMap[table.name] = table);
    return {
      stack: "dbcore",
      transaction: db.transaction.bind(db),
      table(name) {
        const result = tableMap[name];
        if (!result)
          throw new Error(`Table '${name}' not found`);
        return tableMap[name];
      },
      MIN_KEY: -Infinity,
      MAX_KEY: getMaxKey(IdbKeyRange),
      schema
    };
  }
  function createMiddlewareStack(stackImpl, middlewares) {
    return middlewares.reduce((down, { create }) => ({ ...down, ...create(down) }), stackImpl);
  }
  function createMiddlewareStacks(middlewares, idbdb, { IDBKeyRange, indexedDB: indexedDB2 }, tmpTrans) {
    const dbcore = createMiddlewareStack(createDBCore(idbdb, IDBKeyRange, tmpTrans), middlewares.dbcore);
    return {
      dbcore
    };
  }
  function generateMiddlewareStacks({ _novip: db }, tmpTrans) {
    const idbdb = tmpTrans.db;
    const stacks = createMiddlewareStacks(db._middlewares, idbdb, db._deps, tmpTrans);
    db.core = stacks.dbcore;
    db.tables.forEach((table) => {
      const tableName = table.name;
      if (db.core.schema.tables.some((tbl) => tbl.name === tableName)) {
        table.core = db.core.table(tableName);
        if (db[tableName] instanceof db.Table) {
          db[tableName].core = table.core;
        }
      }
    });
  }
  function setApiOnPlace({ _novip: db }, objs, tableNames, dbschema) {
    tableNames.forEach((tableName) => {
      const schema = dbschema[tableName];
      objs.forEach((obj) => {
        const propDesc = getPropertyDescriptor(obj, tableName);
        if (!propDesc || "value" in propDesc && propDesc.value === void 0) {
          if (obj === db.Transaction.prototype || obj instanceof db.Transaction) {
            setProp(obj, tableName, {
              get() {
                return this.table(tableName);
              },
              set(value) {
                defineProperty(this, tableName, { value, writable: true, configurable: true, enumerable: true });
              }
            });
          } else {
            obj[tableName] = new db.Table(tableName, schema);
          }
        }
      });
    });
  }
  function removeTablesApi({ _novip: db }, objs) {
    objs.forEach((obj) => {
      for (let key in obj) {
        if (obj[key] instanceof db.Table)
          delete obj[key];
      }
    });
  }
  function lowerVersionFirst(a, b) {
    return a._cfg.version - b._cfg.version;
  }
  function runUpgraders(db, oldVersion, idbUpgradeTrans, reject) {
    const globalSchema = db._dbSchema;
    const trans = db._createTransaction("readwrite", db._storeNames, globalSchema);
    trans.create(idbUpgradeTrans);
    trans._completion.catch(reject);
    const rejectTransaction = trans._reject.bind(trans);
    const transless = PSD.transless || PSD;
    newScope(() => {
      PSD.trans = trans;
      PSD.transless = transless;
      if (oldVersion === 0) {
        keys(globalSchema).forEach((tableName) => {
          createTable(idbUpgradeTrans, tableName, globalSchema[tableName].primKey, globalSchema[tableName].indexes);
        });
        generateMiddlewareStacks(db, idbUpgradeTrans);
        DexiePromise.follow(() => db.on.populate.fire(trans)).catch(rejectTransaction);
      } else
        updateTablesAndIndexes(db, oldVersion, trans, idbUpgradeTrans).catch(rejectTransaction);
    });
  }
  function updateTablesAndIndexes({ _novip: db }, oldVersion, trans, idbUpgradeTrans) {
    const queue = [];
    const versions = db._versions;
    let globalSchema = db._dbSchema = buildGlobalSchema(db, db.idbdb, idbUpgradeTrans);
    let anyContentUpgraderHasRun = false;
    const versToRun = versions.filter((v) => v._cfg.version >= oldVersion);
    versToRun.forEach((version) => {
      queue.push(() => {
        const oldSchema = globalSchema;
        const newSchema = version._cfg.dbschema;
        adjustToExistingIndexNames(db, oldSchema, idbUpgradeTrans);
        adjustToExistingIndexNames(db, newSchema, idbUpgradeTrans);
        globalSchema = db._dbSchema = newSchema;
        const diff = getSchemaDiff(oldSchema, newSchema);
        diff.add.forEach((tuple) => {
          createTable(idbUpgradeTrans, tuple[0], tuple[1].primKey, tuple[1].indexes);
        });
        diff.change.forEach((change) => {
          if (change.recreate) {
            throw new exceptions.Upgrade("Not yet support for changing primary key");
          } else {
            const store = idbUpgradeTrans.objectStore(change.name);
            change.add.forEach((idx) => addIndex(store, idx));
            change.change.forEach((idx) => {
              store.deleteIndex(idx.name);
              addIndex(store, idx);
            });
            change.del.forEach((idxName) => store.deleteIndex(idxName));
          }
        });
        const contentUpgrade = version._cfg.contentUpgrade;
        if (contentUpgrade && version._cfg.version > oldVersion) {
          generateMiddlewareStacks(db, idbUpgradeTrans);
          trans._memoizedTables = {};
          anyContentUpgraderHasRun = true;
          let upgradeSchema = shallowClone(newSchema);
          diff.del.forEach((table) => {
            upgradeSchema[table] = oldSchema[table];
          });
          removeTablesApi(db, [db.Transaction.prototype]);
          setApiOnPlace(db, [db.Transaction.prototype], keys(upgradeSchema), upgradeSchema);
          trans.schema = upgradeSchema;
          const contentUpgradeIsAsync = isAsyncFunction(contentUpgrade);
          if (contentUpgradeIsAsync) {
            incrementExpectedAwaits();
          }
          let returnValue;
          const promiseFollowed = DexiePromise.follow(() => {
            returnValue = contentUpgrade(trans);
            if (returnValue) {
              if (contentUpgradeIsAsync) {
                var decrementor = decrementExpectedAwaits.bind(null, null);
                returnValue.then(decrementor, decrementor);
              }
            }
          });
          return returnValue && typeof returnValue.then === "function" ? DexiePromise.resolve(returnValue) : promiseFollowed.then(() => returnValue);
        }
      });
      queue.push((idbtrans) => {
        if (!anyContentUpgraderHasRun || !hasIEDeleteObjectStoreBug) {
          const newSchema = version._cfg.dbschema;
          deleteRemovedTables(newSchema, idbtrans);
        }
        removeTablesApi(db, [db.Transaction.prototype]);
        setApiOnPlace(db, [db.Transaction.prototype], db._storeNames, db._dbSchema);
        trans.schema = db._dbSchema;
      });
    });
    function runQueue() {
      return queue.length ? DexiePromise.resolve(queue.shift()(trans.idbtrans)).then(runQueue) : DexiePromise.resolve();
    }
    return runQueue().then(() => {
      createMissingTables(globalSchema, idbUpgradeTrans);
    });
  }
  function getSchemaDiff(oldSchema, newSchema) {
    const diff = {
      del: [],
      add: [],
      change: []
    };
    let table;
    for (table in oldSchema) {
      if (!newSchema[table])
        diff.del.push(table);
    }
    for (table in newSchema) {
      const oldDef = oldSchema[table], newDef = newSchema[table];
      if (!oldDef) {
        diff.add.push([table, newDef]);
      } else {
        const change = {
          name: table,
          def: newDef,
          recreate: false,
          del: [],
          add: [],
          change: []
        };
        if ("" + (oldDef.primKey.keyPath || "") !== "" + (newDef.primKey.keyPath || "") || oldDef.primKey.auto !== newDef.primKey.auto && !isIEOrEdge) {
          change.recreate = true;
          diff.change.push(change);
        } else {
          const oldIndexes = oldDef.idxByName;
          const newIndexes = newDef.idxByName;
          let idxName;
          for (idxName in oldIndexes) {
            if (!newIndexes[idxName])
              change.del.push(idxName);
          }
          for (idxName in newIndexes) {
            const oldIdx = oldIndexes[idxName], newIdx = newIndexes[idxName];
            if (!oldIdx)
              change.add.push(newIdx);
            else if (oldIdx.src !== newIdx.src)
              change.change.push(newIdx);
          }
          if (change.del.length > 0 || change.add.length > 0 || change.change.length > 0) {
            diff.change.push(change);
          }
        }
      }
    }
    return diff;
  }
  function createTable(idbtrans, tableName, primKey, indexes) {
    const store = idbtrans.db.createObjectStore(tableName, primKey.keyPath ? { keyPath: primKey.keyPath, autoIncrement: primKey.auto } : { autoIncrement: primKey.auto });
    indexes.forEach((idx) => addIndex(store, idx));
    return store;
  }
  function createMissingTables(newSchema, idbtrans) {
    keys(newSchema).forEach((tableName) => {
      if (!idbtrans.db.objectStoreNames.contains(tableName)) {
        createTable(idbtrans, tableName, newSchema[tableName].primKey, newSchema[tableName].indexes);
      }
    });
  }
  function deleteRemovedTables(newSchema, idbtrans) {
    [].slice.call(idbtrans.db.objectStoreNames).forEach((storeName) => newSchema[storeName] == null && idbtrans.db.deleteObjectStore(storeName));
  }
  function addIndex(store, idx) {
    store.createIndex(idx.name, idx.keyPath, { unique: idx.unique, multiEntry: idx.multi });
  }
  function buildGlobalSchema(db, idbdb, tmpTrans) {
    const globalSchema = {};
    const dbStoreNames = slice(idbdb.objectStoreNames, 0);
    dbStoreNames.forEach((storeName) => {
      const store = tmpTrans.objectStore(storeName);
      let keyPath = store.keyPath;
      const primKey = createIndexSpec(nameFromKeyPath(keyPath), keyPath || "", false, false, !!store.autoIncrement, keyPath && typeof keyPath !== "string", true);
      const indexes = [];
      for (let j = 0; j < store.indexNames.length; ++j) {
        const idbindex = store.index(store.indexNames[j]);
        keyPath = idbindex.keyPath;
        var index = createIndexSpec(idbindex.name, keyPath, !!idbindex.unique, !!idbindex.multiEntry, false, keyPath && typeof keyPath !== "string", false);
        indexes.push(index);
      }
      globalSchema[storeName] = createTableSchema(storeName, primKey, indexes);
    });
    return globalSchema;
  }
  function readGlobalSchema({ _novip: db }, idbdb, tmpTrans) {
    db.verno = idbdb.version / 10;
    const globalSchema = db._dbSchema = buildGlobalSchema(db, idbdb, tmpTrans);
    db._storeNames = slice(idbdb.objectStoreNames, 0);
    setApiOnPlace(db, [db._allTables], keys(globalSchema), globalSchema);
  }
  function verifyInstalledSchema(db, tmpTrans) {
    const installedSchema = buildGlobalSchema(db, db.idbdb, tmpTrans);
    const diff = getSchemaDiff(installedSchema, db._dbSchema);
    return !(diff.add.length || diff.change.some((ch) => ch.add.length || ch.change.length));
  }
  function adjustToExistingIndexNames({ _novip: db }, schema, idbtrans) {
    const storeNames = idbtrans.db.objectStoreNames;
    for (let i = 0; i < storeNames.length; ++i) {
      const storeName = storeNames[i];
      const store = idbtrans.objectStore(storeName);
      db._hasGetAll = "getAll" in store;
      for (let j = 0; j < store.indexNames.length; ++j) {
        const indexName = store.indexNames[j];
        const keyPath = store.index(indexName).keyPath;
        const dexieName = typeof keyPath === "string" ? keyPath : "[" + slice(keyPath).join("+") + "]";
        if (schema[storeName]) {
          const indexSpec = schema[storeName].idxByName[dexieName];
          if (indexSpec) {
            indexSpec.name = indexName;
            delete schema[storeName].idxByName[dexieName];
            schema[storeName].idxByName[indexName] = indexSpec;
          }
        }
      }
    }
    if (typeof navigator !== "undefined" && /Safari/.test(navigator.userAgent) && !/(Chrome\/|Edge\/)/.test(navigator.userAgent) && _global.WorkerGlobalScope && _global instanceof _global.WorkerGlobalScope && [].concat(navigator.userAgent.match(/Safari\/(\d*)/))[1] < 604) {
      db._hasGetAll = false;
    }
  }
  function parseIndexSyntax(primKeyAndIndexes) {
    return primKeyAndIndexes.split(",").map((index, indexNum) => {
      index = index.trim();
      const name = index.replace(/([&*]|\+\+)/g, "");
      const keyPath = /^\[/.test(name) ? name.match(/^\[(.*)\]$/)[1].split("+") : name;
      return createIndexSpec(name, keyPath || null, /\&/.test(index), /\*/.test(index), /\+\+/.test(index), isArray(keyPath), indexNum === 0);
    });
  }
  function createVersionConstructor(db) {
    return makeClassConstructor(Version.prototype, function Version2(versionNumber) {
      this.db = db;
      this._cfg = {
        version: versionNumber,
        storesSource: null,
        dbschema: {},
        tables: {},
        contentUpgrade: null
      };
    });
  }
  function getDbNamesTable(indexedDB2, IDBKeyRange) {
    let dbNamesDB = indexedDB2["_dbNamesDB"];
    if (!dbNamesDB) {
      dbNamesDB = indexedDB2["_dbNamesDB"] = new Dexie$1(DBNAMES_DB, {
        addons: [],
        indexedDB: indexedDB2,
        IDBKeyRange
      });
      dbNamesDB.version(1).stores({ dbnames: "name" });
    }
    return dbNamesDB.table("dbnames");
  }
  function hasDatabasesNative(indexedDB2) {
    return indexedDB2 && typeof indexedDB2.databases === "function";
  }
  function getDatabaseNames({ indexedDB: indexedDB2, IDBKeyRange }) {
    return hasDatabasesNative(indexedDB2) ? Promise.resolve(indexedDB2.databases()).then((infos) => infos.map((info) => info.name).filter((name) => name !== DBNAMES_DB)) : getDbNamesTable(indexedDB2, IDBKeyRange).toCollection().primaryKeys();
  }
  function _onDatabaseCreated({ indexedDB: indexedDB2, IDBKeyRange }, name) {
    !hasDatabasesNative(indexedDB2) && name !== DBNAMES_DB && getDbNamesTable(indexedDB2, IDBKeyRange).put({ name }).catch(nop);
  }
  function _onDatabaseDeleted({ indexedDB: indexedDB2, IDBKeyRange }, name) {
    !hasDatabasesNative(indexedDB2) && name !== DBNAMES_DB && getDbNamesTable(indexedDB2, IDBKeyRange).delete(name).catch(nop);
  }
  function vip(fn) {
    return newScope(function() {
      PSD.letThrough = true;
      return fn();
    });
  }
  function idbReady() {
    var isSafari = !navigator.userAgentData && /Safari\//.test(navigator.userAgent) && !/Chrom(e|ium)\//.test(navigator.userAgent);
    if (!isSafari || !indexedDB.databases)
      return Promise.resolve();
    var intervalId;
    return new Promise(function(resolve) {
      var tryIdb = function() {
        return indexedDB.databases().finally(resolve);
      };
      intervalId = setInterval(tryIdb, 100);
      tryIdb();
    }).finally(function() {
      return clearInterval(intervalId);
    });
  }
  function dexieOpen(db) {
    const state2 = db._state;
    const { indexedDB: indexedDB2 } = db._deps;
    if (state2.isBeingOpened || db.idbdb)
      return state2.dbReadyPromise.then(() => state2.dbOpenError ? rejection(state2.dbOpenError) : db);
    debug && (state2.openCanceller._stackHolder = getErrorWithStack());
    state2.isBeingOpened = true;
    state2.dbOpenError = null;
    state2.openComplete = false;
    const openCanceller = state2.openCanceller;
    function throwIfCancelled() {
      if (state2.openCanceller !== openCanceller)
        throw new exceptions.DatabaseClosed("db.open() was cancelled");
    }
    let resolveDbReady = state2.dbReadyResolve, upgradeTransaction = null, wasCreated = false;
    const tryOpenDB = () => new DexiePromise((resolve, reject) => {
      throwIfCancelled();
      if (!indexedDB2)
        throw new exceptions.MissingAPI();
      const dbName = db.name;
      const req = state2.autoSchema ? indexedDB2.open(dbName) : indexedDB2.open(dbName, Math.round(db.verno * 10));
      if (!req)
        throw new exceptions.MissingAPI();
      req.onerror = eventRejectHandler(reject);
      req.onblocked = wrap(db._fireOnBlocked);
      req.onupgradeneeded = wrap((e) => {
        upgradeTransaction = req.transaction;
        if (state2.autoSchema && !db._options.allowEmptyDB) {
          req.onerror = preventDefault;
          upgradeTransaction.abort();
          req.result.close();
          const delreq = indexedDB2.deleteDatabase(dbName);
          delreq.onsuccess = delreq.onerror = wrap(() => {
            reject(new exceptions.NoSuchDatabase(`Database ${dbName} doesnt exist`));
          });
        } else {
          upgradeTransaction.onerror = eventRejectHandler(reject);
          var oldVer = e.oldVersion > Math.pow(2, 62) ? 0 : e.oldVersion;
          wasCreated = oldVer < 1;
          db._novip.idbdb = req.result;
          runUpgraders(db, oldVer / 10, upgradeTransaction, reject);
        }
      }, reject);
      req.onsuccess = wrap(() => {
        upgradeTransaction = null;
        const idbdb = db._novip.idbdb = req.result;
        const objectStoreNames = slice(idbdb.objectStoreNames);
        if (objectStoreNames.length > 0)
          try {
            const tmpTrans = idbdb.transaction(safariMultiStoreFix(objectStoreNames), "readonly");
            if (state2.autoSchema)
              readGlobalSchema(db, idbdb, tmpTrans);
            else {
              adjustToExistingIndexNames(db, db._dbSchema, tmpTrans);
              if (!verifyInstalledSchema(db, tmpTrans)) {
                console.warn(`Dexie SchemaDiff: Schema was extended without increasing the number passed to db.version(). Some queries may fail.`);
              }
            }
            generateMiddlewareStacks(db, tmpTrans);
          } catch (e) {
          }
        connections.push(db);
        idbdb.onversionchange = wrap((ev) => {
          state2.vcFired = true;
          db.on("versionchange").fire(ev);
        });
        idbdb.onclose = wrap((ev) => {
          db.on("close").fire(ev);
        });
        if (wasCreated)
          _onDatabaseCreated(db._deps, dbName);
        resolve();
      }, reject);
    }).catch((err) => {
      if (err && err.name === "UnknownError" && state2.PR1398_maxLoop > 0) {
        state2.PR1398_maxLoop--;
        console.warn("Dexie: Workaround for Chrome UnknownError on open()");
        return tryOpenDB();
      } else {
        return DexiePromise.reject(err);
      }
    });
    return DexiePromise.race([
      openCanceller,
      (typeof navigator === "undefined" ? DexiePromise.resolve() : idbReady()).then(tryOpenDB)
    ]).then(() => {
      throwIfCancelled();
      state2.onReadyBeingFired = [];
      return DexiePromise.resolve(vip(() => db.on.ready.fire(db.vip))).then(function fireRemainders() {
        if (state2.onReadyBeingFired.length > 0) {
          let remainders = state2.onReadyBeingFired.reduce(promisableChain, nop);
          state2.onReadyBeingFired = [];
          return DexiePromise.resolve(vip(() => remainders(db.vip))).then(fireRemainders);
        }
      });
    }).finally(() => {
      state2.onReadyBeingFired = null;
      state2.isBeingOpened = false;
    }).then(() => {
      return db;
    }).catch((err) => {
      state2.dbOpenError = err;
      try {
        upgradeTransaction && upgradeTransaction.abort();
      } catch (_a) {
      }
      if (openCanceller === state2.openCanceller) {
        db._close();
      }
      return rejection(err);
    }).finally(() => {
      state2.openComplete = true;
      resolveDbReady();
    });
  }
  function awaitIterator(iterator) {
    var callNext = (result) => iterator.next(result), doThrow = (error) => iterator.throw(error), onSuccess = step(callNext), onError = step(doThrow);
    function step(getNext) {
      return (val) => {
        var next = getNext(val), value = next.value;
        return next.done ? value : !value || typeof value.then !== "function" ? isArray(value) ? Promise.all(value).then(onSuccess, onError) : onSuccess(value) : value.then(onSuccess, onError);
      };
    }
    return step(callNext)();
  }
  function extractTransactionArgs(mode, _tableArgs_, scopeFunc) {
    var i = arguments.length;
    if (i < 2)
      throw new exceptions.InvalidArgument("Too few arguments");
    var args = new Array(i - 1);
    while (--i)
      args[i - 1] = arguments[i];
    scopeFunc = args.pop();
    var tables = flatten(args);
    return [mode, tables, scopeFunc];
  }
  function enterTransactionScope(db, mode, storeNames, parentTransaction, scopeFunc) {
    return DexiePromise.resolve().then(() => {
      const transless = PSD.transless || PSD;
      const trans = db._createTransaction(mode, storeNames, db._dbSchema, parentTransaction);
      const zoneProps = {
        trans,
        transless
      };
      if (parentTransaction) {
        trans.idbtrans = parentTransaction.idbtrans;
      } else {
        try {
          trans.create();
          db._state.PR1398_maxLoop = 3;
        } catch (ex) {
          if (ex.name === errnames.InvalidState && db.isOpen() && --db._state.PR1398_maxLoop > 0) {
            console.warn("Dexie: Need to reopen db");
            db._close();
            return db.open().then(() => enterTransactionScope(db, mode, storeNames, null, scopeFunc));
          }
          return rejection(ex);
        }
      }
      const scopeFuncIsAsync = isAsyncFunction(scopeFunc);
      if (scopeFuncIsAsync) {
        incrementExpectedAwaits();
      }
      let returnValue;
      const promiseFollowed = DexiePromise.follow(() => {
        returnValue = scopeFunc.call(trans, trans);
        if (returnValue) {
          if (scopeFuncIsAsync) {
            var decrementor = decrementExpectedAwaits.bind(null, null);
            returnValue.then(decrementor, decrementor);
          } else if (typeof returnValue.next === "function" && typeof returnValue.throw === "function") {
            returnValue = awaitIterator(returnValue);
          }
        }
      }, zoneProps);
      return (returnValue && typeof returnValue.then === "function" ? DexiePromise.resolve(returnValue).then((x) => trans.active ? x : rejection(new exceptions.PrematureCommit("Transaction committed too early. See http://bit.ly/2kdckMn"))) : promiseFollowed.then(() => returnValue)).then((x) => {
        if (parentTransaction)
          trans._resolve();
        return trans._completion.then(() => x);
      }).catch((e) => {
        trans._reject(e);
        return rejection(e);
      });
    });
  }
  function pad(a, value, count) {
    const result = isArray(a) ? a.slice() : [a];
    for (let i = 0; i < count; ++i)
      result.push(value);
    return result;
  }
  function createVirtualIndexMiddleware(down) {
    return {
      ...down,
      table(tableName) {
        const table = down.table(tableName);
        const { schema } = table;
        const indexLookup = {};
        const allVirtualIndexes = [];
        function addVirtualIndexes(keyPath, keyTail, lowLevelIndex) {
          const keyPathAlias = getKeyPathAlias(keyPath);
          const indexList = indexLookup[keyPathAlias] = indexLookup[keyPathAlias] || [];
          const keyLength = keyPath == null ? 0 : typeof keyPath === "string" ? 1 : keyPath.length;
          const isVirtual = keyTail > 0;
          const virtualIndex = {
            ...lowLevelIndex,
            isVirtual,
            keyTail,
            keyLength,
            extractKey: getKeyExtractor(keyPath),
            unique: !isVirtual && lowLevelIndex.unique
          };
          indexList.push(virtualIndex);
          if (!virtualIndex.isPrimaryKey) {
            allVirtualIndexes.push(virtualIndex);
          }
          if (keyLength > 1) {
            const virtualKeyPath = keyLength === 2 ? keyPath[0] : keyPath.slice(0, keyLength - 1);
            addVirtualIndexes(virtualKeyPath, keyTail + 1, lowLevelIndex);
          }
          indexList.sort((a, b) => a.keyTail - b.keyTail);
          return virtualIndex;
        }
        const primaryKey = addVirtualIndexes(schema.primaryKey.keyPath, 0, schema.primaryKey);
        indexLookup[":id"] = [primaryKey];
        for (const index of schema.indexes) {
          addVirtualIndexes(index.keyPath, 0, index);
        }
        function findBestIndex(keyPath) {
          const result2 = indexLookup[getKeyPathAlias(keyPath)];
          return result2 && result2[0];
        }
        function translateRange(range, keyTail) {
          return {
            type: range.type === 1 ? 2 : range.type,
            lower: pad(range.lower, range.lowerOpen ? down.MAX_KEY : down.MIN_KEY, keyTail),
            lowerOpen: true,
            upper: pad(range.upper, range.upperOpen ? down.MIN_KEY : down.MAX_KEY, keyTail),
            upperOpen: true
          };
        }
        function translateRequest(req) {
          const index = req.query.index;
          return index.isVirtual ? {
            ...req,
            query: {
              index,
              range: translateRange(req.query.range, index.keyTail)
            }
          } : req;
        }
        const result = {
          ...table,
          schema: {
            ...schema,
            primaryKey,
            indexes: allVirtualIndexes,
            getIndexByKeyPath: findBestIndex
          },
          count(req) {
            return table.count(translateRequest(req));
          },
          query(req) {
            return table.query(translateRequest(req));
          },
          openCursor(req) {
            const { keyTail, isVirtual, keyLength } = req.query.index;
            if (!isVirtual)
              return table.openCursor(req);
            function createVirtualCursor(cursor) {
              function _continue(key) {
                key != null ? cursor.continue(pad(key, req.reverse ? down.MAX_KEY : down.MIN_KEY, keyTail)) : req.unique ? cursor.continue(cursor.key.slice(0, keyLength).concat(req.reverse ? down.MIN_KEY : down.MAX_KEY, keyTail)) : cursor.continue();
              }
              const virtualCursor = Object.create(cursor, {
                continue: { value: _continue },
                continuePrimaryKey: {
                  value(key, primaryKey2) {
                    cursor.continuePrimaryKey(pad(key, down.MAX_KEY, keyTail), primaryKey2);
                  }
                },
                primaryKey: {
                  get() {
                    return cursor.primaryKey;
                  }
                },
                key: {
                  get() {
                    const key = cursor.key;
                    return keyLength === 1 ? key[0] : key.slice(0, keyLength);
                  }
                },
                value: {
                  get() {
                    return cursor.value;
                  }
                }
              });
              return virtualCursor;
            }
            return table.openCursor(translateRequest(req)).then((cursor) => cursor && createVirtualCursor(cursor));
          }
        };
        return result;
      }
    };
  }
  function getObjectDiff(a, b, rv, prfx) {
    rv = rv || {};
    prfx = prfx || "";
    keys(a).forEach((prop) => {
      if (!hasOwn(b, prop)) {
        rv[prfx + prop] = void 0;
      } else {
        var ap = a[prop], bp = b[prop];
        if (typeof ap === "object" && typeof bp === "object" && ap && bp) {
          const apTypeName = toStringTag(ap);
          const bpTypeName = toStringTag(bp);
          if (apTypeName !== bpTypeName) {
            rv[prfx + prop] = b[prop];
          } else if (apTypeName === "Object") {
            getObjectDiff(ap, bp, rv, prfx + prop + ".");
          } else if (ap !== bp) {
            rv[prfx + prop] = b[prop];
          }
        } else if (ap !== bp)
          rv[prfx + prop] = b[prop];
      }
    });
    keys(b).forEach((prop) => {
      if (!hasOwn(a, prop)) {
        rv[prfx + prop] = b[prop];
      }
    });
    return rv;
  }
  function getEffectiveKeys(primaryKey, req) {
    if (req.type === "delete")
      return req.keys;
    return req.keys || req.values.map(primaryKey.extractKey);
  }
  function getExistingValues(table, req, effectiveKeys) {
    return req.type === "add" ? Promise.resolve([]) : table.getMany({ trans: req.trans, keys: effectiveKeys, cache: "immutable" });
  }
  function getFromTransactionCache(keys2, cache, clone) {
    try {
      if (!cache)
        return null;
      if (cache.keys.length < keys2.length)
        return null;
      const result = [];
      for (let i = 0, j = 0; i < cache.keys.length && j < keys2.length; ++i) {
        if (cmp(cache.keys[i], keys2[j]) !== 0)
          continue;
        result.push(clone ? deepClone(cache.values[i]) : cache.values[i]);
        ++j;
      }
      return result.length === keys2.length ? result : null;
    } catch (_a) {
      return null;
    }
  }
  function isEmptyRange(node) {
    return !("from" in node);
  }
  function addRange(target, from, to) {
    const diff = cmp(from, to);
    if (isNaN(diff))
      return;
    if (diff > 0)
      throw RangeError();
    if (isEmptyRange(target))
      return extend(target, { from, to, d: 1 });
    const left = target.l;
    const right = target.r;
    if (cmp(to, target.from) < 0) {
      left ? addRange(left, from, to) : target.l = { from, to, d: 1, l: null, r: null };
      return rebalance(target);
    }
    if (cmp(from, target.to) > 0) {
      right ? addRange(right, from, to) : target.r = { from, to, d: 1, l: null, r: null };
      return rebalance(target);
    }
    if (cmp(from, target.from) < 0) {
      target.from = from;
      target.l = null;
      target.d = right ? right.d + 1 : 1;
    }
    if (cmp(to, target.to) > 0) {
      target.to = to;
      target.r = null;
      target.d = target.l ? target.l.d + 1 : 1;
    }
    const rightWasCutOff = !target.r;
    if (left && !target.l) {
      mergeRanges(target, left);
    }
    if (right && rightWasCutOff) {
      mergeRanges(target, right);
    }
  }
  function mergeRanges(target, newSet) {
    function _addRangeSet(target2, { from, to, l, r }) {
      addRange(target2, from, to);
      if (l)
        _addRangeSet(target2, l);
      if (r)
        _addRangeSet(target2, r);
    }
    if (!isEmptyRange(newSet))
      _addRangeSet(target, newSet);
  }
  function rangesOverlap(rangeSet1, rangeSet2) {
    const i1 = getRangeSetIterator(rangeSet2);
    let nextResult1 = i1.next();
    if (nextResult1.done)
      return false;
    let a = nextResult1.value;
    const i2 = getRangeSetIterator(rangeSet1);
    let nextResult2 = i2.next(a.from);
    let b = nextResult2.value;
    while (!nextResult1.done && !nextResult2.done) {
      if (cmp(b.from, a.to) <= 0 && cmp(b.to, a.from) >= 0)
        return true;
      cmp(a.from, b.from) < 0 ? a = (nextResult1 = i1.next(b.from)).value : b = (nextResult2 = i2.next(a.from)).value;
    }
    return false;
  }
  function getRangeSetIterator(node) {
    let state2 = isEmptyRange(node) ? null : { s: 0, n: node };
    return {
      next(key) {
        const keyProvided = arguments.length > 0;
        while (state2) {
          switch (state2.s) {
            case 0:
              state2.s = 1;
              if (keyProvided) {
                while (state2.n.l && cmp(key, state2.n.from) < 0)
                  state2 = { up: state2, n: state2.n.l, s: 1 };
              } else {
                while (state2.n.l)
                  state2 = { up: state2, n: state2.n.l, s: 1 };
              }
            case 1:
              state2.s = 2;
              if (!keyProvided || cmp(key, state2.n.to) <= 0)
                return { value: state2.n, done: false };
            case 2:
              if (state2.n.r) {
                state2.s = 3;
                state2 = { up: state2, n: state2.n.r, s: 0 };
                continue;
              }
            case 3:
              state2 = state2.up;
          }
        }
        return { done: true };
      }
    };
  }
  function rebalance(target) {
    var _a, _b;
    const diff = (((_a = target.r) === null || _a === void 0 ? void 0 : _a.d) || 0) - (((_b = target.l) === null || _b === void 0 ? void 0 : _b.d) || 0);
    const r = diff > 1 ? "r" : diff < -1 ? "l" : "";
    if (r) {
      const l = r === "r" ? "l" : "r";
      const rootClone = { ...target };
      const oldRootRight = target[r];
      target.from = oldRootRight.from;
      target.to = oldRootRight.to;
      target[r] = oldRootRight[r];
      rootClone[r] = oldRootRight[l];
      target[l] = rootClone;
      rootClone.d = computeDepth(rootClone);
    }
    target.d = computeDepth(target);
  }
  function computeDepth({ r, l }) {
    return (r ? l ? Math.max(r.d, l.d) : r.d : l ? l.d : 0) + 1;
  }
  function trackAffectedIndexes(getRangeSet, schema, oldObjs, newObjs) {
    function addAffectedIndex(ix) {
      const rangeSet = getRangeSet(ix.name || "");
      function extractKey(obj) {
        return obj != null ? ix.extractKey(obj) : null;
      }
      const addKeyOrKeys = (key) => ix.multiEntry && isArray(key) ? key.forEach((key2) => rangeSet.addKey(key2)) : rangeSet.addKey(key);
      (oldObjs || newObjs).forEach((_, i) => {
        const oldKey = oldObjs && extractKey(oldObjs[i]);
        const newKey = newObjs && extractKey(newObjs[i]);
        if (cmp(oldKey, newKey) !== 0) {
          if (oldKey != null)
            addKeyOrKeys(oldKey);
          if (newKey != null)
            addKeyOrKeys(newKey);
        }
      });
    }
    schema.indexes.forEach(addAffectedIndex);
  }
  function extendObservabilitySet(target, newSet) {
    keys(newSet).forEach((part) => {
      const rangeSet = target[part] || (target[part] = new RangeSet());
      mergeRanges(rangeSet, newSet[part]);
    });
    return target;
  }
  function liveQuery(querier) {
    let hasValue = false;
    let currentValue = void 0;
    const observable = new Observable((observer) => {
      const scopeFuncIsAsync = isAsyncFunction(querier);
      function execute(subscr) {
        if (scopeFuncIsAsync) {
          incrementExpectedAwaits();
        }
        const exec = () => newScope(querier, { subscr, trans: null });
        const rv = PSD.trans ? usePSD(PSD.transless, exec) : exec();
        if (scopeFuncIsAsync) {
          rv.then(decrementExpectedAwaits, decrementExpectedAwaits);
        }
        return rv;
      }
      let closed = false;
      let accumMuts = {};
      let currentObs = {};
      const subscription = {
        get closed() {
          return closed;
        },
        unsubscribe: () => {
          closed = true;
          globalEvents.storagemutated.unsubscribe(mutationListener);
        }
      };
      observer.start && observer.start(subscription);
      let querying = false, startedListening = false;
      function shouldNotify() {
        return keys(currentObs).some((key) => accumMuts[key] && rangesOverlap(accumMuts[key], currentObs[key]));
      }
      const mutationListener = (parts) => {
        extendObservabilitySet(accumMuts, parts);
        if (shouldNotify()) {
          doQuery();
        }
      };
      const doQuery = () => {
        if (querying || closed)
          return;
        accumMuts = {};
        const subscr = {};
        const ret = execute(subscr);
        if (!startedListening) {
          globalEvents(DEXIE_STORAGE_MUTATED_EVENT_NAME, mutationListener);
          startedListening = true;
        }
        querying = true;
        Promise.resolve(ret).then((result) => {
          hasValue = true;
          currentValue = result;
          querying = false;
          if (closed)
            return;
          if (shouldNotify()) {
            doQuery();
          } else {
            accumMuts = {};
            currentObs = subscr;
            observer.next && observer.next(result);
          }
        }, (err) => {
          querying = false;
          hasValue = false;
          observer.error && observer.error(err);
          subscription.unsubscribe();
        });
      };
      doQuery();
      return subscription;
    });
    observable.hasValue = () => hasValue;
    observable.getValue = () => currentValue;
    return observable;
  }
  function propagateLocally(updateParts) {
    let wasMe = propagatingLocally;
    try {
      propagatingLocally = true;
      globalEvents.storagemutated.fire(updateParts);
    } finally {
      propagatingLocally = wasMe;
    }
  }
  function propagateMessageLocally({ data }) {
    if (data && data.type === STORAGE_MUTATED_DOM_EVENT_NAME) {
      propagateLocally(data.changedParts);
    }
  }
  var _global, keys, isArray, getProto, _hasOwn, defineProperty, getOwnPropertyDescriptor, _slice, concat, intrinsicTypeNames, intrinsicTypes, circularRefs, toString, iteratorSymbol, getIteratorOf, NO_CHAR_ARRAY, isAsyncFunction, debug, libraryFilter, NEEDS_THROW_FOR_STACK, dexieErrorNames, idbDomErrorNames, errorList, defaultTexts, errnames, BaseException, exceptions, exceptionMap, fullNameExceptions, INTERNAL, LONG_STACKS_CLIP_LIMIT, MAX_LONG_STACKS, ZONE_ECHO_LIMIT, resolvedNativePromise, nativePromiseProto, resolvedGlobalPromise, nativePromiseThen, NativePromise, patchGlobalPromise, stack_being_generated, schedulePhysicalTick, asap, isOutsideMicroTick, needsNewPhysicalTick, unhandledErrors, rejectingErrors, currentFulfiller, rejectionMapper, globalPSD, PSD, microtickQueue, numScheduledCalls, tickFinalizers, thenProp, task, taskCounter, zoneStack, zoneEchoes, totalEchoes, zone_id_counter, UNHANDLEDREJECTION, rejection, DEXIE_VERSION, maxString, minKey, INVALID_KEY_ARGUMENT, STRING_EXPECTED, connections, isIEOrEdge, hasIEDeleteObjectStoreBug, hangsOnDeleteLargeKeyRange, dexieStackFrameFilter, DBNAMES_DB, READONLY, READWRITE, AnyRange, Table, Collection, deleteCallback, WhereClause, DEXIE_STORAGE_MUTATED_EVENT_NAME, STORAGE_MUTATED_DOM_EVENT_NAME, globalEvents, Transaction, getMaxKey, _id_counter, Version, virtualIndexMiddleware, hooksMiddleware, cacheExistingValuesMiddleware, RangeSet, observabilityMiddleware, Dexie$1, symbolObservable, Observable, domDeps, Dexie, propagatingLocally;
  var init_dexie = __esm({
    "node_modules/dexie/dist/modern/dexie.mjs"() {
      _global = typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : global;
      keys = Object.keys;
      isArray = Array.isArray;
      if (typeof Promise !== "undefined" && !_global.Promise) {
        _global.Promise = Promise;
      }
      getProto = Object.getPrototypeOf;
      _hasOwn = {}.hasOwnProperty;
      defineProperty = Object.defineProperty;
      getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
      _slice = [].slice;
      concat = [].concat;
      intrinsicTypeNames = "BigUint64Array,BigInt64Array,Array,Boolean,String,Date,RegExp,Blob,File,FileList,FileSystemFileHandle,FileSystemDirectoryHandle,ArrayBuffer,DataView,Uint8ClampedArray,ImageBitmap,ImageData,Map,Set,CryptoKey".split(",").concat(flatten([8, 16, 32, 64].map((num) => ["Int", "Uint", "Float"].map((t) => t + num + "Array")))).filter((t) => _global[t]);
      intrinsicTypes = intrinsicTypeNames.map((t) => _global[t]);
      arrayToObject(intrinsicTypeNames, (x) => [x, true]);
      circularRefs = null;
      ({ toString } = {});
      iteratorSymbol = typeof Symbol !== "undefined" ? Symbol.iterator : "@@iterator";
      getIteratorOf = typeof iteratorSymbol === "symbol" ? function(x) {
        var i;
        return x != null && (i = x[iteratorSymbol]) && i.apply(x);
      } : function() {
        return null;
      };
      NO_CHAR_ARRAY = {};
      isAsyncFunction = typeof Symbol !== "undefined" ? (fn) => fn[Symbol.toStringTag] === "AsyncFunction" : () => false;
      debug = typeof location !== "undefined" && /^(http|https):\/\/(localhost|127\.0\.0\.1)/.test(location.href);
      libraryFilter = () => true;
      NEEDS_THROW_FOR_STACK = !new Error("").stack;
      dexieErrorNames = [
        "Modify",
        "Bulk",
        "OpenFailed",
        "VersionChange",
        "Schema",
        "Upgrade",
        "InvalidTable",
        "MissingAPI",
        "NoSuchDatabase",
        "InvalidArgument",
        "SubTransaction",
        "Unsupported",
        "Internal",
        "DatabaseClosed",
        "PrematureCommit",
        "ForeignAwait"
      ];
      idbDomErrorNames = [
        "Unknown",
        "Constraint",
        "Data",
        "TransactionInactive",
        "ReadOnly",
        "Version",
        "NotFound",
        "InvalidState",
        "InvalidAccess",
        "Abort",
        "Timeout",
        "QuotaExceeded",
        "Syntax",
        "DataClone"
      ];
      errorList = dexieErrorNames.concat(idbDomErrorNames);
      defaultTexts = {
        VersionChanged: "Database version changed by other database connection",
        DatabaseClosed: "Database has been closed",
        Abort: "Transaction aborted",
        TransactionInactive: "Transaction has already completed or failed",
        MissingAPI: "IndexedDB API missing. Please visit https://tinyurl.com/y2uuvskb"
      };
      derive(DexieError).from(Error).extend({
        stack: {
          get: function() {
            return this._stack || (this._stack = this.name + ": " + this.message + prettyStack(this._e, 2));
          }
        },
        toString: function() {
          return this.name + ": " + this.message;
        }
      });
      derive(ModifyError).from(DexieError);
      derive(BulkError).from(DexieError);
      errnames = errorList.reduce((obj, name) => (obj[name] = name + "Error", obj), {});
      BaseException = DexieError;
      exceptions = errorList.reduce((obj, name) => {
        var fullName = name + "Error";
        function DexieError2(msgOrInner, inner) {
          this._e = getErrorWithStack();
          this.name = fullName;
          if (!msgOrInner) {
            this.message = defaultTexts[name] || fullName;
            this.inner = null;
          } else if (typeof msgOrInner === "string") {
            this.message = `${msgOrInner}${!inner ? "" : "\n " + inner}`;
            this.inner = inner || null;
          } else if (typeof msgOrInner === "object") {
            this.message = `${msgOrInner.name} ${msgOrInner.message}`;
            this.inner = msgOrInner;
          }
        }
        derive(DexieError2).from(BaseException);
        obj[name] = DexieError2;
        return obj;
      }, {});
      exceptions.Syntax = SyntaxError;
      exceptions.Type = TypeError;
      exceptions.Range = RangeError;
      exceptionMap = idbDomErrorNames.reduce((obj, name) => {
        obj[name + "Error"] = exceptions[name];
        return obj;
      }, {});
      fullNameExceptions = errorList.reduce((obj, name) => {
        if (["Syntax", "Type", "Range"].indexOf(name) === -1)
          obj[name + "Error"] = exceptions[name];
        return obj;
      }, {});
      fullNameExceptions.ModifyError = ModifyError;
      fullNameExceptions.DexieError = DexieError;
      fullNameExceptions.BulkError = BulkError;
      INTERNAL = {};
      LONG_STACKS_CLIP_LIMIT = 100;
      MAX_LONG_STACKS = 20;
      ZONE_ECHO_LIMIT = 100;
      [resolvedNativePromise, nativePromiseProto, resolvedGlobalPromise] = typeof Promise === "undefined" ? [] : (() => {
        let globalP = Promise.resolve();
        if (typeof crypto === "undefined" || !crypto.subtle)
          return [globalP, getProto(globalP), globalP];
        const nativeP = crypto.subtle.digest("SHA-512", new Uint8Array([0]));
        return [
          nativeP,
          getProto(nativeP),
          globalP
        ];
      })();
      nativePromiseThen = nativePromiseProto && nativePromiseProto.then;
      NativePromise = resolvedNativePromise && resolvedNativePromise.constructor;
      patchGlobalPromise = !!resolvedGlobalPromise;
      stack_being_generated = false;
      schedulePhysicalTick = resolvedGlobalPromise ? () => {
        resolvedGlobalPromise.then(physicalTick);
      } : _global.setImmediate ? setImmediate.bind(null, physicalTick) : _global.MutationObserver ? () => {
        var hiddenDiv = document.createElement("div");
        new MutationObserver(() => {
          physicalTick();
          hiddenDiv = null;
        }).observe(hiddenDiv, { attributes: true });
        hiddenDiv.setAttribute("i", "1");
      } : () => {
        setTimeout(physicalTick, 0);
      };
      asap = function(callback, args) {
        microtickQueue.push([callback, args]);
        if (needsNewPhysicalTick) {
          schedulePhysicalTick();
          needsNewPhysicalTick = false;
        }
      };
      isOutsideMicroTick = true;
      needsNewPhysicalTick = true;
      unhandledErrors = [];
      rejectingErrors = [];
      currentFulfiller = null;
      rejectionMapper = mirror;
      globalPSD = {
        id: "global",
        global: true,
        ref: 0,
        unhandleds: [],
        onunhandled: globalError,
        pgp: false,
        env: {},
        finalize: function() {
          this.unhandleds.forEach((uh) => {
            try {
              globalError(uh[0], uh[1]);
            } catch (e) {
            }
          });
        }
      };
      PSD = globalPSD;
      microtickQueue = [];
      numScheduledCalls = 0;
      tickFinalizers = [];
      thenProp = {
        get: function() {
          var psd = PSD, microTaskId = totalEchoes;
          function then(onFulfilled, onRejected) {
            var possibleAwait = !psd.global && (psd !== PSD || microTaskId !== totalEchoes);
            const cleanup = possibleAwait && !decrementExpectedAwaits();
            var rv = new DexiePromise((resolve, reject) => {
              propagateToListener(this, new Listener(nativeAwaitCompatibleWrap(onFulfilled, psd, possibleAwait, cleanup), nativeAwaitCompatibleWrap(onRejected, psd, possibleAwait, cleanup), resolve, reject, psd));
            });
            debug && linkToPreviousPromise(rv, this);
            return rv;
          }
          then.prototype = INTERNAL;
          return then;
        },
        set: function(value) {
          setProp(this, "then", value && value.prototype === INTERNAL ? thenProp : {
            get: function() {
              return value;
            },
            set: thenProp.set
          });
        }
      };
      props(DexiePromise.prototype, {
        then: thenProp,
        _then: function(onFulfilled, onRejected) {
          propagateToListener(this, new Listener(null, null, onFulfilled, onRejected, PSD));
        },
        catch: function(onRejected) {
          if (arguments.length === 1)
            return this.then(null, onRejected);
          var type2 = arguments[0], handler = arguments[1];
          return typeof type2 === "function" ? this.then(null, (err) => err instanceof type2 ? handler(err) : PromiseReject(err)) : this.then(null, (err) => err && err.name === type2 ? handler(err) : PromiseReject(err));
        },
        finally: function(onFinally) {
          return this.then((value) => {
            onFinally();
            return value;
          }, (err) => {
            onFinally();
            return PromiseReject(err);
          });
        },
        stack: {
          get: function() {
            if (this._stack)
              return this._stack;
            try {
              stack_being_generated = true;
              var stacks = getStack(this, [], MAX_LONG_STACKS);
              var stack = stacks.join("\nFrom previous: ");
              if (this._state !== null)
                this._stack = stack;
              return stack;
            } finally {
              stack_being_generated = false;
            }
          }
        },
        timeout: function(ms, msg) {
          return ms < Infinity ? new DexiePromise((resolve, reject) => {
            var handle = setTimeout(() => reject(new exceptions.Timeout(msg)), ms);
            this.then(resolve, reject).finally(clearTimeout.bind(null, handle));
          }) : this;
        }
      });
      if (typeof Symbol !== "undefined" && Symbol.toStringTag)
        setProp(DexiePromise.prototype, Symbol.toStringTag, "Dexie.Promise");
      globalPSD.env = snapShot();
      props(DexiePromise, {
        all: function() {
          var values = getArrayOf.apply(null, arguments).map(onPossibleParallellAsync);
          return new DexiePromise(function(resolve, reject) {
            if (values.length === 0)
              resolve([]);
            var remaining = values.length;
            values.forEach((a, i) => DexiePromise.resolve(a).then((x) => {
              values[i] = x;
              if (!--remaining)
                resolve(values);
            }, reject));
          });
        },
        resolve: (value) => {
          if (value instanceof DexiePromise)
            return value;
          if (value && typeof value.then === "function")
            return new DexiePromise((resolve, reject) => {
              value.then(resolve, reject);
            });
          var rv = new DexiePromise(INTERNAL, true, value);
          linkToPreviousPromise(rv, currentFulfiller);
          return rv;
        },
        reject: PromiseReject,
        race: function() {
          var values = getArrayOf.apply(null, arguments).map(onPossibleParallellAsync);
          return new DexiePromise((resolve, reject) => {
            values.map((value) => DexiePromise.resolve(value).then(resolve, reject));
          });
        },
        PSD: {
          get: () => PSD,
          set: (value) => PSD = value
        },
        totalEchoes: { get: () => totalEchoes },
        newPSD: newScope,
        usePSD,
        scheduler: {
          get: () => asap,
          set: (value) => {
            asap = value;
          }
        },
        rejectionMapper: {
          get: () => rejectionMapper,
          set: (value) => {
            rejectionMapper = value;
          }
        },
        follow: (fn, zoneProps) => {
          return new DexiePromise((resolve, reject) => {
            return newScope((resolve2, reject2) => {
              var psd = PSD;
              psd.unhandleds = [];
              psd.onunhandled = reject2;
              psd.finalize = callBoth(function() {
                run_at_end_of_this_or_next_physical_tick(() => {
                  this.unhandleds.length === 0 ? resolve2() : reject2(this.unhandleds[0]);
                });
              }, psd.finalize);
              fn();
            }, zoneProps, resolve, reject);
          });
        }
      });
      if (NativePromise) {
        if (NativePromise.allSettled)
          setProp(DexiePromise, "allSettled", function() {
            const possiblePromises = getArrayOf.apply(null, arguments).map(onPossibleParallellAsync);
            return new DexiePromise((resolve) => {
              if (possiblePromises.length === 0)
                resolve([]);
              let remaining = possiblePromises.length;
              const results = new Array(remaining);
              possiblePromises.forEach((p, i) => DexiePromise.resolve(p).then((value) => results[i] = { status: "fulfilled", value }, (reason) => results[i] = { status: "rejected", reason }).then(() => --remaining || resolve(results)));
            });
          });
        if (NativePromise.any && typeof AggregateError !== "undefined")
          setProp(DexiePromise, "any", function() {
            const possiblePromises = getArrayOf.apply(null, arguments).map(onPossibleParallellAsync);
            return new DexiePromise((resolve, reject) => {
              if (possiblePromises.length === 0)
                reject(new AggregateError([]));
              let remaining = possiblePromises.length;
              const failures = new Array(remaining);
              possiblePromises.forEach((p, i) => DexiePromise.resolve(p).then((value) => resolve(value), (failure) => {
                failures[i] = failure;
                if (!--remaining)
                  reject(new AggregateError(failures));
              }));
            });
          });
      }
      task = { awaits: 0, echoes: 0, id: 0 };
      taskCounter = 0;
      zoneStack = [];
      zoneEchoes = 0;
      totalEchoes = 0;
      zone_id_counter = 0;
      if (("" + nativePromiseThen).indexOf("[native code]") === -1) {
        incrementExpectedAwaits = decrementExpectedAwaits = nop;
      }
      UNHANDLEDREJECTION = "unhandledrejection";
      rejection = DexiePromise.reject;
      DEXIE_VERSION = "3.2.7";
      maxString = String.fromCharCode(65535);
      minKey = -Infinity;
      INVALID_KEY_ARGUMENT = "Invalid key provided. Keys must be of type string, number, Date or Array<string | number | Date>.";
      STRING_EXPECTED = "String expected.";
      connections = [];
      isIEOrEdge = typeof navigator !== "undefined" && /(MSIE|Trident|Edge)/.test(navigator.userAgent);
      hasIEDeleteObjectStoreBug = isIEOrEdge;
      hangsOnDeleteLargeKeyRange = isIEOrEdge;
      dexieStackFrameFilter = (frame) => !/(dexie\.js|dexie\.min\.js)/.test(frame);
      DBNAMES_DB = "__dbnames";
      READONLY = "readonly";
      READWRITE = "readwrite";
      AnyRange = {
        type: 3,
        lower: -Infinity,
        lowerOpen: false,
        upper: [[]],
        upperOpen: false
      };
      Table = class {
        _trans(mode, fn, writeLocked) {
          const trans = this._tx || PSD.trans;
          const tableName = this.name;
          function checkTableInTransaction(resolve, reject, trans2) {
            if (!trans2.schema[tableName])
              throw new exceptions.NotFound("Table " + tableName + " not part of transaction");
            return fn(trans2.idbtrans, trans2);
          }
          const wasRootExec = beginMicroTickScope();
          try {
            return trans && trans.db === this.db ? trans === PSD.trans ? trans._promise(mode, checkTableInTransaction, writeLocked) : newScope(() => trans._promise(mode, checkTableInTransaction, writeLocked), { trans, transless: PSD.transless || PSD }) : tempTransaction(this.db, mode, [this.name], checkTableInTransaction);
          } finally {
            if (wasRootExec)
              endMicroTickScope();
          }
        }
        get(keyOrCrit, cb) {
          if (keyOrCrit && keyOrCrit.constructor === Object)
            return this.where(keyOrCrit).first(cb);
          return this._trans("readonly", (trans) => {
            return this.core.get({ trans, key: keyOrCrit }).then((res) => this.hook.reading.fire(res));
          }).then(cb);
        }
        where(indexOrCrit) {
          if (typeof indexOrCrit === "string")
            return new this.db.WhereClause(this, indexOrCrit);
          if (isArray(indexOrCrit))
            return new this.db.WhereClause(this, `[${indexOrCrit.join("+")}]`);
          const keyPaths = keys(indexOrCrit);
          if (keyPaths.length === 1)
            return this.where(keyPaths[0]).equals(indexOrCrit[keyPaths[0]]);
          const compoundIndex = this.schema.indexes.concat(this.schema.primKey).filter((ix) => {
            if (ix.compound && keyPaths.every((keyPath) => ix.keyPath.indexOf(keyPath) >= 0)) {
              for (let i = 0; i < keyPaths.length; ++i) {
                if (keyPaths.indexOf(ix.keyPath[i]) === -1)
                  return false;
              }
              return true;
            }
            return false;
          }).sort((a, b) => a.keyPath.length - b.keyPath.length)[0];
          if (compoundIndex && this.db._maxKey !== maxString) {
            const keyPathsInValidOrder = compoundIndex.keyPath.slice(0, keyPaths.length);
            return this.where(keyPathsInValidOrder).equals(keyPathsInValidOrder.map((kp) => indexOrCrit[kp]));
          }
          if (!compoundIndex && debug)
            console.warn(`The query ${JSON.stringify(indexOrCrit)} on ${this.name} would benefit of a compound index [${keyPaths.join("+")}]`);
          const { idxByName } = this.schema;
          const idb = this.db._deps.indexedDB;
          function equals(a, b) {
            try {
              return idb.cmp(a, b) === 0;
            } catch (e) {
              return false;
            }
          }
          const [idx, filterFunction] = keyPaths.reduce(([prevIndex, prevFilterFn], keyPath) => {
            const index = idxByName[keyPath];
            const value = indexOrCrit[keyPath];
            return [
              prevIndex || index,
              prevIndex || !index ? combine(prevFilterFn, index && index.multi ? (x) => {
                const prop = getByKeyPath(x, keyPath);
                return isArray(prop) && prop.some((item) => equals(value, item));
              } : (x) => equals(value, getByKeyPath(x, keyPath))) : prevFilterFn
            ];
          }, [null, null]);
          return idx ? this.where(idx.name).equals(indexOrCrit[idx.keyPath]).filter(filterFunction) : compoundIndex ? this.filter(filterFunction) : this.where(keyPaths).equals("");
        }
        filter(filterFunction) {
          return this.toCollection().and(filterFunction);
        }
        count(thenShortcut) {
          return this.toCollection().count(thenShortcut);
        }
        offset(offset) {
          return this.toCollection().offset(offset);
        }
        limit(numRows) {
          return this.toCollection().limit(numRows);
        }
        each(callback) {
          return this.toCollection().each(callback);
        }
        toArray(thenShortcut) {
          return this.toCollection().toArray(thenShortcut);
        }
        toCollection() {
          return new this.db.Collection(new this.db.WhereClause(this));
        }
        orderBy(index) {
          return new this.db.Collection(new this.db.WhereClause(this, isArray(index) ? `[${index.join("+")}]` : index));
        }
        reverse() {
          return this.toCollection().reverse();
        }
        mapToClass(constructor) {
          this.schema.mappedClass = constructor;
          const readHook = (obj) => {
            if (!obj)
              return obj;
            const res = Object.create(constructor.prototype);
            for (var m in obj)
              if (hasOwn(obj, m))
                try {
                  res[m] = obj[m];
                } catch (_) {
                }
            return res;
          };
          if (this.schema.readHook) {
            this.hook.reading.unsubscribe(this.schema.readHook);
          }
          this.schema.readHook = readHook;
          this.hook("reading", readHook);
          return constructor;
        }
        defineClass() {
          function Class(content) {
            extend(this, content);
          }
          return this.mapToClass(Class);
        }
        add(obj, key) {
          const { auto, keyPath } = this.schema.primKey;
          let objToAdd = obj;
          if (keyPath && auto) {
            objToAdd = workaroundForUndefinedPrimKey(keyPath)(obj);
          }
          return this._trans("readwrite", (trans) => {
            return this.core.mutate({ trans, type: "add", keys: key != null ? [key] : null, values: [objToAdd] });
          }).then((res) => res.numFailures ? DexiePromise.reject(res.failures[0]) : res.lastResult).then((lastResult) => {
            if (keyPath) {
              try {
                setByKeyPath(obj, keyPath, lastResult);
              } catch (_) {
              }
            }
            return lastResult;
          });
        }
        update(keyOrObject, modifications) {
          if (typeof keyOrObject === "object" && !isArray(keyOrObject)) {
            const key = getByKeyPath(keyOrObject, this.schema.primKey.keyPath);
            if (key === void 0)
              return rejection(new exceptions.InvalidArgument("Given object does not contain its primary key"));
            try {
              if (typeof modifications !== "function") {
                keys(modifications).forEach((keyPath) => {
                  setByKeyPath(keyOrObject, keyPath, modifications[keyPath]);
                });
              } else {
                modifications(keyOrObject, { value: keyOrObject, primKey: key });
              }
            } catch (_a) {
            }
            return this.where(":id").equals(key).modify(modifications);
          } else {
            return this.where(":id").equals(keyOrObject).modify(modifications);
          }
        }
        put(obj, key) {
          const { auto, keyPath } = this.schema.primKey;
          let objToAdd = obj;
          if (keyPath && auto) {
            objToAdd = workaroundForUndefinedPrimKey(keyPath)(obj);
          }
          return this._trans("readwrite", (trans) => this.core.mutate({ trans, type: "put", values: [objToAdd], keys: key != null ? [key] : null })).then((res) => res.numFailures ? DexiePromise.reject(res.failures[0]) : res.lastResult).then((lastResult) => {
            if (keyPath) {
              try {
                setByKeyPath(obj, keyPath, lastResult);
              } catch (_) {
              }
            }
            return lastResult;
          });
        }
        delete(key) {
          return this._trans("readwrite", (trans) => this.core.mutate({ trans, type: "delete", keys: [key] })).then((res) => res.numFailures ? DexiePromise.reject(res.failures[0]) : void 0);
        }
        clear() {
          return this._trans("readwrite", (trans) => this.core.mutate({ trans, type: "deleteRange", range: AnyRange })).then((res) => res.numFailures ? DexiePromise.reject(res.failures[0]) : void 0);
        }
        bulkGet(keys2) {
          return this._trans("readonly", (trans) => {
            return this.core.getMany({
              keys: keys2,
              trans
            }).then((result) => result.map((res) => this.hook.reading.fire(res)));
          });
        }
        bulkAdd(objects, keysOrOptions, options) {
          const keys2 = Array.isArray(keysOrOptions) ? keysOrOptions : void 0;
          options = options || (keys2 ? void 0 : keysOrOptions);
          const wantResults = options ? options.allKeys : void 0;
          return this._trans("readwrite", (trans) => {
            const { auto, keyPath } = this.schema.primKey;
            if (keyPath && keys2)
              throw new exceptions.InvalidArgument("bulkAdd(): keys argument invalid on tables with inbound keys");
            if (keys2 && keys2.length !== objects.length)
              throw new exceptions.InvalidArgument("Arguments objects and keys must have the same length");
            const numObjects = objects.length;
            let objectsToAdd = keyPath && auto ? objects.map(workaroundForUndefinedPrimKey(keyPath)) : objects;
            return this.core.mutate({ trans, type: "add", keys: keys2, values: objectsToAdd, wantResults }).then(({ numFailures, results, lastResult, failures }) => {
              const result = wantResults ? results : lastResult;
              if (numFailures === 0)
                return result;
              throw new BulkError(`${this.name}.bulkAdd(): ${numFailures} of ${numObjects} operations failed`, failures);
            });
          });
        }
        bulkPut(objects, keysOrOptions, options) {
          const keys2 = Array.isArray(keysOrOptions) ? keysOrOptions : void 0;
          options = options || (keys2 ? void 0 : keysOrOptions);
          const wantResults = options ? options.allKeys : void 0;
          return this._trans("readwrite", (trans) => {
            const { auto, keyPath } = this.schema.primKey;
            if (keyPath && keys2)
              throw new exceptions.InvalidArgument("bulkPut(): keys argument invalid on tables with inbound keys");
            if (keys2 && keys2.length !== objects.length)
              throw new exceptions.InvalidArgument("Arguments objects and keys must have the same length");
            const numObjects = objects.length;
            let objectsToPut = keyPath && auto ? objects.map(workaroundForUndefinedPrimKey(keyPath)) : objects;
            return this.core.mutate({ trans, type: "put", keys: keys2, values: objectsToPut, wantResults }).then(({ numFailures, results, lastResult, failures }) => {
              const result = wantResults ? results : lastResult;
              if (numFailures === 0)
                return result;
              throw new BulkError(`${this.name}.bulkPut(): ${numFailures} of ${numObjects} operations failed`, failures);
            });
          });
        }
        bulkDelete(keys2) {
          const numKeys = keys2.length;
          return this._trans("readwrite", (trans) => {
            return this.core.mutate({ trans, type: "delete", keys: keys2 });
          }).then(({ numFailures, lastResult, failures }) => {
            if (numFailures === 0)
              return lastResult;
            throw new BulkError(`${this.name}.bulkDelete(): ${numFailures} of ${numKeys} operations failed`, failures);
          });
        }
      };
      Collection = class {
        _read(fn, cb) {
          var ctx = this._ctx;
          return ctx.error ? ctx.table._trans(null, rejection.bind(null, ctx.error)) : ctx.table._trans("readonly", fn).then(cb);
        }
        _write(fn) {
          var ctx = this._ctx;
          return ctx.error ? ctx.table._trans(null, rejection.bind(null, ctx.error)) : ctx.table._trans("readwrite", fn, "locked");
        }
        _addAlgorithm(fn) {
          var ctx = this._ctx;
          ctx.algorithm = combine(ctx.algorithm, fn);
        }
        _iterate(fn, coreTrans) {
          return iter(this._ctx, fn, coreTrans, this._ctx.table.core);
        }
        clone(props2) {
          var rv = Object.create(this.constructor.prototype), ctx = Object.create(this._ctx);
          if (props2)
            extend(ctx, props2);
          rv._ctx = ctx;
          return rv;
        }
        raw() {
          this._ctx.valueMapper = null;
          return this;
        }
        each(fn) {
          var ctx = this._ctx;
          return this._read((trans) => iter(ctx, fn, trans, ctx.table.core));
        }
        count(cb) {
          return this._read((trans) => {
            const ctx = this._ctx;
            const coreTable = ctx.table.core;
            if (isPlainKeyRange(ctx, true)) {
              return coreTable.count({
                trans,
                query: {
                  index: getIndexOrStore(ctx, coreTable.schema),
                  range: ctx.range
                }
              }).then((count2) => Math.min(count2, ctx.limit));
            } else {
              var count = 0;
              return iter(ctx, () => {
                ++count;
                return false;
              }, trans, coreTable).then(() => count);
            }
          }).then(cb);
        }
        sortBy(keyPath, cb) {
          const parts = keyPath.split(".").reverse(), lastPart = parts[0], lastIndex = parts.length - 1;
          function getval(obj, i) {
            if (i)
              return getval(obj[parts[i]], i - 1);
            return obj[lastPart];
          }
          var order = this._ctx.dir === "next" ? 1 : -1;
          function sorter(a, b) {
            var aVal = getval(a, lastIndex), bVal = getval(b, lastIndex);
            return aVal < bVal ? -order : aVal > bVal ? order : 0;
          }
          return this.toArray(function(a) {
            return a.sort(sorter);
          }).then(cb);
        }
        toArray(cb) {
          return this._read((trans) => {
            var ctx = this._ctx;
            if (ctx.dir === "next" && isPlainKeyRange(ctx, true) && ctx.limit > 0) {
              const { valueMapper } = ctx;
              const index = getIndexOrStore(ctx, ctx.table.core.schema);
              return ctx.table.core.query({
                trans,
                limit: ctx.limit,
                values: true,
                query: {
                  index,
                  range: ctx.range
                }
              }).then(({ result }) => valueMapper ? result.map(valueMapper) : result);
            } else {
              const a = [];
              return iter(ctx, (item) => a.push(item), trans, ctx.table.core).then(() => a);
            }
          }, cb);
        }
        offset(offset) {
          var ctx = this._ctx;
          if (offset <= 0)
            return this;
          ctx.offset += offset;
          if (isPlainKeyRange(ctx)) {
            addReplayFilter(ctx, () => {
              var offsetLeft = offset;
              return (cursor, advance) => {
                if (offsetLeft === 0)
                  return true;
                if (offsetLeft === 1) {
                  --offsetLeft;
                  return false;
                }
                advance(() => {
                  cursor.advance(offsetLeft);
                  offsetLeft = 0;
                });
                return false;
              };
            });
          } else {
            addReplayFilter(ctx, () => {
              var offsetLeft = offset;
              return () => --offsetLeft < 0;
            });
          }
          return this;
        }
        limit(numRows) {
          this._ctx.limit = Math.min(this._ctx.limit, numRows);
          addReplayFilter(this._ctx, () => {
            var rowsLeft = numRows;
            return function(cursor, advance, resolve) {
              if (--rowsLeft <= 0)
                advance(resolve);
              return rowsLeft >= 0;
            };
          }, true);
          return this;
        }
        until(filterFunction, bIncludeStopEntry) {
          addFilter(this._ctx, function(cursor, advance, resolve) {
            if (filterFunction(cursor.value)) {
              advance(resolve);
              return bIncludeStopEntry;
            } else {
              return true;
            }
          });
          return this;
        }
        first(cb) {
          return this.limit(1).toArray(function(a) {
            return a[0];
          }).then(cb);
        }
        last(cb) {
          return this.reverse().first(cb);
        }
        filter(filterFunction) {
          addFilter(this._ctx, function(cursor) {
            return filterFunction(cursor.value);
          });
          addMatchFilter(this._ctx, filterFunction);
          return this;
        }
        and(filter) {
          return this.filter(filter);
        }
        or(indexName) {
          return new this.db.WhereClause(this._ctx.table, indexName, this);
        }
        reverse() {
          this._ctx.dir = this._ctx.dir === "prev" ? "next" : "prev";
          if (this._ondirectionchange)
            this._ondirectionchange(this._ctx.dir);
          return this;
        }
        desc() {
          return this.reverse();
        }
        eachKey(cb) {
          var ctx = this._ctx;
          ctx.keysOnly = !ctx.isMatch;
          return this.each(function(val, cursor) {
            cb(cursor.key, cursor);
          });
        }
        eachUniqueKey(cb) {
          this._ctx.unique = "unique";
          return this.eachKey(cb);
        }
        eachPrimaryKey(cb) {
          var ctx = this._ctx;
          ctx.keysOnly = !ctx.isMatch;
          return this.each(function(val, cursor) {
            cb(cursor.primaryKey, cursor);
          });
        }
        keys(cb) {
          var ctx = this._ctx;
          ctx.keysOnly = !ctx.isMatch;
          var a = [];
          return this.each(function(item, cursor) {
            a.push(cursor.key);
          }).then(function() {
            return a;
          }).then(cb);
        }
        primaryKeys(cb) {
          var ctx = this._ctx;
          if (ctx.dir === "next" && isPlainKeyRange(ctx, true) && ctx.limit > 0) {
            return this._read((trans) => {
              var index = getIndexOrStore(ctx, ctx.table.core.schema);
              return ctx.table.core.query({
                trans,
                values: false,
                limit: ctx.limit,
                query: {
                  index,
                  range: ctx.range
                }
              });
            }).then(({ result }) => result).then(cb);
          }
          ctx.keysOnly = !ctx.isMatch;
          var a = [];
          return this.each(function(item, cursor) {
            a.push(cursor.primaryKey);
          }).then(function() {
            return a;
          }).then(cb);
        }
        uniqueKeys(cb) {
          this._ctx.unique = "unique";
          return this.keys(cb);
        }
        firstKey(cb) {
          return this.limit(1).keys(function(a) {
            return a[0];
          }).then(cb);
        }
        lastKey(cb) {
          return this.reverse().firstKey(cb);
        }
        distinct() {
          var ctx = this._ctx, idx = ctx.index && ctx.table.schema.idxByName[ctx.index];
          if (!idx || !idx.multi)
            return this;
          var set = {};
          addFilter(this._ctx, function(cursor) {
            var strKey = cursor.primaryKey.toString();
            var found = hasOwn(set, strKey);
            set[strKey] = true;
            return !found;
          });
          return this;
        }
        modify(changes) {
          var ctx = this._ctx;
          return this._write((trans) => {
            var modifyer;
            if (typeof changes === "function") {
              modifyer = changes;
            } else {
              var keyPaths = keys(changes);
              var numKeys = keyPaths.length;
              modifyer = function(item) {
                var anythingModified = false;
                for (var i = 0; i < numKeys; ++i) {
                  var keyPath = keyPaths[i], val = changes[keyPath];
                  if (getByKeyPath(item, keyPath) !== val) {
                    setByKeyPath(item, keyPath, val);
                    anythingModified = true;
                  }
                }
                return anythingModified;
              };
            }
            const coreTable = ctx.table.core;
            const { outbound, extractKey } = coreTable.schema.primaryKey;
            const limit = this.db._options.modifyChunkSize || 200;
            const totalFailures = [];
            let successCount = 0;
            const failedKeys = [];
            const applyMutateResult = (expectedCount, res) => {
              const { failures, numFailures } = res;
              successCount += expectedCount - numFailures;
              for (let pos of keys(failures)) {
                totalFailures.push(failures[pos]);
              }
            };
            return this.clone().primaryKeys().then((keys2) => {
              const nextChunk = (offset) => {
                const count = Math.min(limit, keys2.length - offset);
                return coreTable.getMany({
                  trans,
                  keys: keys2.slice(offset, offset + count),
                  cache: "immutable"
                }).then((values) => {
                  const addValues = [];
                  const putValues = [];
                  const putKeys = outbound ? [] : null;
                  const deleteKeys = [];
                  for (let i = 0; i < count; ++i) {
                    const origValue = values[i];
                    const ctx2 = {
                      value: deepClone(origValue),
                      primKey: keys2[offset + i]
                    };
                    if (modifyer.call(ctx2, ctx2.value, ctx2) !== false) {
                      if (ctx2.value == null) {
                        deleteKeys.push(keys2[offset + i]);
                      } else if (!outbound && cmp(extractKey(origValue), extractKey(ctx2.value)) !== 0) {
                        deleteKeys.push(keys2[offset + i]);
                        addValues.push(ctx2.value);
                      } else {
                        putValues.push(ctx2.value);
                        if (outbound)
                          putKeys.push(keys2[offset + i]);
                      }
                    }
                  }
                  const criteria = isPlainKeyRange(ctx) && ctx.limit === Infinity && (typeof changes !== "function" || changes === deleteCallback) && {
                    index: ctx.index,
                    range: ctx.range
                  };
                  return Promise.resolve(addValues.length > 0 && coreTable.mutate({ trans, type: "add", values: addValues }).then((res) => {
                    for (let pos in res.failures) {
                      deleteKeys.splice(parseInt(pos), 1);
                    }
                    applyMutateResult(addValues.length, res);
                  })).then(() => (putValues.length > 0 || criteria && typeof changes === "object") && coreTable.mutate({
                    trans,
                    type: "put",
                    keys: putKeys,
                    values: putValues,
                    criteria,
                    changeSpec: typeof changes !== "function" && changes
                  }).then((res) => applyMutateResult(putValues.length, res))).then(() => (deleteKeys.length > 0 || criteria && changes === deleteCallback) && coreTable.mutate({
                    trans,
                    type: "delete",
                    keys: deleteKeys,
                    criteria
                  }).then((res) => applyMutateResult(deleteKeys.length, res))).then(() => {
                    return keys2.length > offset + count && nextChunk(offset + limit);
                  });
                });
              };
              return nextChunk(0).then(() => {
                if (totalFailures.length > 0)
                  throw new ModifyError("Error modifying one or more objects", totalFailures, successCount, failedKeys);
                return keys2.length;
              });
            });
          });
        }
        delete() {
          var ctx = this._ctx, range = ctx.range;
          if (isPlainKeyRange(ctx) && (ctx.isPrimKey && !hangsOnDeleteLargeKeyRange || range.type === 3)) {
            return this._write((trans) => {
              const { primaryKey } = ctx.table.core.schema;
              const coreRange = range;
              return ctx.table.core.count({ trans, query: { index: primaryKey, range: coreRange } }).then((count) => {
                return ctx.table.core.mutate({ trans, type: "deleteRange", range: coreRange }).then(({ failures, lastResult, results, numFailures }) => {
                  if (numFailures)
                    throw new ModifyError("Could not delete some values", Object.keys(failures).map((pos) => failures[pos]), count - numFailures);
                  return count - numFailures;
                });
              });
            });
          }
          return this.modify(deleteCallback);
        }
      };
      deleteCallback = (value, ctx) => ctx.value = null;
      WhereClause = class {
        get Collection() {
          return this._ctx.table.db.Collection;
        }
        between(lower, upper, includeLower, includeUpper) {
          includeLower = includeLower !== false;
          includeUpper = includeUpper === true;
          try {
            if (this._cmp(lower, upper) > 0 || this._cmp(lower, upper) === 0 && (includeLower || includeUpper) && !(includeLower && includeUpper))
              return emptyCollection(this);
            return new this.Collection(this, () => createRange(lower, upper, !includeLower, !includeUpper));
          } catch (e) {
            return fail(this, INVALID_KEY_ARGUMENT);
          }
        }
        equals(value) {
          if (value == null)
            return fail(this, INVALID_KEY_ARGUMENT);
          return new this.Collection(this, () => rangeEqual(value));
        }
        above(value) {
          if (value == null)
            return fail(this, INVALID_KEY_ARGUMENT);
          return new this.Collection(this, () => createRange(value, void 0, true));
        }
        aboveOrEqual(value) {
          if (value == null)
            return fail(this, INVALID_KEY_ARGUMENT);
          return new this.Collection(this, () => createRange(value, void 0, false));
        }
        below(value) {
          if (value == null)
            return fail(this, INVALID_KEY_ARGUMENT);
          return new this.Collection(this, () => createRange(void 0, value, false, true));
        }
        belowOrEqual(value) {
          if (value == null)
            return fail(this, INVALID_KEY_ARGUMENT);
          return new this.Collection(this, () => createRange(void 0, value));
        }
        startsWith(str) {
          if (typeof str !== "string")
            return fail(this, STRING_EXPECTED);
          return this.between(str, str + maxString, true, true);
        }
        startsWithIgnoreCase(str) {
          if (str === "")
            return this.startsWith(str);
          return addIgnoreCaseAlgorithm(this, (x, a) => x.indexOf(a[0]) === 0, [str], maxString);
        }
        equalsIgnoreCase(str) {
          return addIgnoreCaseAlgorithm(this, (x, a) => x === a[0], [str], "");
        }
        anyOfIgnoreCase() {
          var set = getArrayOf.apply(NO_CHAR_ARRAY, arguments);
          if (set.length === 0)
            return emptyCollection(this);
          return addIgnoreCaseAlgorithm(this, (x, a) => a.indexOf(x) !== -1, set, "");
        }
        startsWithAnyOfIgnoreCase() {
          var set = getArrayOf.apply(NO_CHAR_ARRAY, arguments);
          if (set.length === 0)
            return emptyCollection(this);
          return addIgnoreCaseAlgorithm(this, (x, a) => a.some((n) => x.indexOf(n) === 0), set, maxString);
        }
        anyOf() {
          const set = getArrayOf.apply(NO_CHAR_ARRAY, arguments);
          let compare = this._cmp;
          try {
            set.sort(compare);
          } catch (e) {
            return fail(this, INVALID_KEY_ARGUMENT);
          }
          if (set.length === 0)
            return emptyCollection(this);
          const c = new this.Collection(this, () => createRange(set[0], set[set.length - 1]));
          c._ondirectionchange = (direction) => {
            compare = direction === "next" ? this._ascending : this._descending;
            set.sort(compare);
          };
          let i = 0;
          c._addAlgorithm((cursor, advance, resolve) => {
            const key = cursor.key;
            while (compare(key, set[i]) > 0) {
              ++i;
              if (i === set.length) {
                advance(resolve);
                return false;
              }
            }
            if (compare(key, set[i]) === 0) {
              return true;
            } else {
              advance(() => {
                cursor.continue(set[i]);
              });
              return false;
            }
          });
          return c;
        }
        notEqual(value) {
          return this.inAnyRange([[minKey, value], [value, this.db._maxKey]], { includeLowers: false, includeUppers: false });
        }
        noneOf() {
          const set = getArrayOf.apply(NO_CHAR_ARRAY, arguments);
          if (set.length === 0)
            return new this.Collection(this);
          try {
            set.sort(this._ascending);
          } catch (e) {
            return fail(this, INVALID_KEY_ARGUMENT);
          }
          const ranges = set.reduce((res, val) => res ? res.concat([[res[res.length - 1][1], val]]) : [[minKey, val]], null);
          ranges.push([set[set.length - 1], this.db._maxKey]);
          return this.inAnyRange(ranges, { includeLowers: false, includeUppers: false });
        }
        inAnyRange(ranges, options) {
          const cmp2 = this._cmp, ascending = this._ascending, descending = this._descending, min = this._min, max = this._max;
          if (ranges.length === 0)
            return emptyCollection(this);
          if (!ranges.every((range) => range[0] !== void 0 && range[1] !== void 0 && ascending(range[0], range[1]) <= 0)) {
            return fail(this, "First argument to inAnyRange() must be an Array of two-value Arrays [lower,upper] where upper must not be lower than lower", exceptions.InvalidArgument);
          }
          const includeLowers = !options || options.includeLowers !== false;
          const includeUppers = options && options.includeUppers === true;
          function addRange2(ranges2, newRange) {
            let i = 0, l = ranges2.length;
            for (; i < l; ++i) {
              const range = ranges2[i];
              if (cmp2(newRange[0], range[1]) < 0 && cmp2(newRange[1], range[0]) > 0) {
                range[0] = min(range[0], newRange[0]);
                range[1] = max(range[1], newRange[1]);
                break;
              }
            }
            if (i === l)
              ranges2.push(newRange);
            return ranges2;
          }
          let sortDirection = ascending;
          function rangeSorter(a, b) {
            return sortDirection(a[0], b[0]);
          }
          let set;
          try {
            set = ranges.reduce(addRange2, []);
            set.sort(rangeSorter);
          } catch (ex) {
            return fail(this, INVALID_KEY_ARGUMENT);
          }
          let rangePos = 0;
          const keyIsBeyondCurrentEntry = includeUppers ? (key) => ascending(key, set[rangePos][1]) > 0 : (key) => ascending(key, set[rangePos][1]) >= 0;
          const keyIsBeforeCurrentEntry = includeLowers ? (key) => descending(key, set[rangePos][0]) > 0 : (key) => descending(key, set[rangePos][0]) >= 0;
          function keyWithinCurrentRange(key) {
            return !keyIsBeyondCurrentEntry(key) && !keyIsBeforeCurrentEntry(key);
          }
          let checkKey = keyIsBeyondCurrentEntry;
          const c = new this.Collection(this, () => createRange(set[0][0], set[set.length - 1][1], !includeLowers, !includeUppers));
          c._ondirectionchange = (direction) => {
            if (direction === "next") {
              checkKey = keyIsBeyondCurrentEntry;
              sortDirection = ascending;
            } else {
              checkKey = keyIsBeforeCurrentEntry;
              sortDirection = descending;
            }
            set.sort(rangeSorter);
          };
          c._addAlgorithm((cursor, advance, resolve) => {
            var key = cursor.key;
            while (checkKey(key)) {
              ++rangePos;
              if (rangePos === set.length) {
                advance(resolve);
                return false;
              }
            }
            if (keyWithinCurrentRange(key)) {
              return true;
            } else if (this._cmp(key, set[rangePos][1]) === 0 || this._cmp(key, set[rangePos][0]) === 0) {
              return false;
            } else {
              advance(() => {
                if (sortDirection === ascending)
                  cursor.continue(set[rangePos][0]);
                else
                  cursor.continue(set[rangePos][1]);
              });
              return false;
            }
          });
          return c;
        }
        startsWithAnyOf() {
          const set = getArrayOf.apply(NO_CHAR_ARRAY, arguments);
          if (!set.every((s) => typeof s === "string")) {
            return fail(this, "startsWithAnyOf() only works with strings");
          }
          if (set.length === 0)
            return emptyCollection(this);
          return this.inAnyRange(set.map((str) => [str, str + maxString]));
        }
      };
      DEXIE_STORAGE_MUTATED_EVENT_NAME = "storagemutated";
      STORAGE_MUTATED_DOM_EVENT_NAME = "x-storagemutated-1";
      globalEvents = Events(null, DEXIE_STORAGE_MUTATED_EVENT_NAME);
      Transaction = class {
        _lock() {
          assert(!PSD.global);
          ++this._reculock;
          if (this._reculock === 1 && !PSD.global)
            PSD.lockOwnerFor = this;
          return this;
        }
        _unlock() {
          assert(!PSD.global);
          if (--this._reculock === 0) {
            if (!PSD.global)
              PSD.lockOwnerFor = null;
            while (this._blockedFuncs.length > 0 && !this._locked()) {
              var fnAndPSD = this._blockedFuncs.shift();
              try {
                usePSD(fnAndPSD[1], fnAndPSD[0]);
              } catch (e) {
              }
            }
          }
          return this;
        }
        _locked() {
          return this._reculock && PSD.lockOwnerFor !== this;
        }
        create(idbtrans) {
          if (!this.mode)
            return this;
          const idbdb = this.db.idbdb;
          const dbOpenError = this.db._state.dbOpenError;
          assert(!this.idbtrans);
          if (!idbtrans && !idbdb) {
            switch (dbOpenError && dbOpenError.name) {
              case "DatabaseClosedError":
                throw new exceptions.DatabaseClosed(dbOpenError);
              case "MissingAPIError":
                throw new exceptions.MissingAPI(dbOpenError.message, dbOpenError);
              default:
                throw new exceptions.OpenFailed(dbOpenError);
            }
          }
          if (!this.active)
            throw new exceptions.TransactionInactive();
          assert(this._completion._state === null);
          idbtrans = this.idbtrans = idbtrans || (this.db.core ? this.db.core.transaction(this.storeNames, this.mode, { durability: this.chromeTransactionDurability }) : idbdb.transaction(this.storeNames, this.mode, { durability: this.chromeTransactionDurability }));
          idbtrans.onerror = wrap((ev) => {
            preventDefault(ev);
            this._reject(idbtrans.error);
          });
          idbtrans.onabort = wrap((ev) => {
            preventDefault(ev);
            this.active && this._reject(new exceptions.Abort(idbtrans.error));
            this.active = false;
            this.on("abort").fire(ev);
          });
          idbtrans.oncomplete = wrap(() => {
            this.active = false;
            this._resolve();
            if ("mutatedParts" in idbtrans) {
              globalEvents.storagemutated.fire(idbtrans["mutatedParts"]);
            }
          });
          return this;
        }
        _promise(mode, fn, bWriteLock) {
          if (mode === "readwrite" && this.mode !== "readwrite")
            return rejection(new exceptions.ReadOnly("Transaction is readonly"));
          if (!this.active)
            return rejection(new exceptions.TransactionInactive());
          if (this._locked()) {
            return new DexiePromise((resolve, reject) => {
              this._blockedFuncs.push([() => {
                this._promise(mode, fn, bWriteLock).then(resolve, reject);
              }, PSD]);
            });
          } else if (bWriteLock) {
            return newScope(() => {
              var p2 = new DexiePromise((resolve, reject) => {
                this._lock();
                const rv = fn(resolve, reject, this);
                if (rv && rv.then)
                  rv.then(resolve, reject);
              });
              p2.finally(() => this._unlock());
              p2._lib = true;
              return p2;
            });
          } else {
            var p = new DexiePromise((resolve, reject) => {
              var rv = fn(resolve, reject, this);
              if (rv && rv.then)
                rv.then(resolve, reject);
            });
            p._lib = true;
            return p;
          }
        }
        _root() {
          return this.parent ? this.parent._root() : this;
        }
        waitFor(promiseLike) {
          var root = this._root();
          const promise = DexiePromise.resolve(promiseLike);
          if (root._waitingFor) {
            root._waitingFor = root._waitingFor.then(() => promise);
          } else {
            root._waitingFor = promise;
            root._waitingQueue = [];
            var store = root.idbtrans.objectStore(root.storeNames[0]);
            (function spin() {
              ++root._spinCount;
              while (root._waitingQueue.length)
                root._waitingQueue.shift()();
              if (root._waitingFor)
                store.get(-Infinity).onsuccess = spin;
            })();
          }
          var currentWaitPromise = root._waitingFor;
          return new DexiePromise((resolve, reject) => {
            promise.then((res) => root._waitingQueue.push(wrap(resolve.bind(null, res))), (err) => root._waitingQueue.push(wrap(reject.bind(null, err)))).finally(() => {
              if (root._waitingFor === currentWaitPromise) {
                root._waitingFor = null;
              }
            });
          });
        }
        abort() {
          if (this.active) {
            this.active = false;
            if (this.idbtrans)
              this.idbtrans.abort();
            this._reject(new exceptions.Abort());
          }
        }
        table(tableName) {
          const memoizedTables = this._memoizedTables || (this._memoizedTables = {});
          if (hasOwn(memoizedTables, tableName))
            return memoizedTables[tableName];
          const tableSchema = this.schema[tableName];
          if (!tableSchema) {
            throw new exceptions.NotFound("Table " + tableName + " not part of transaction");
          }
          const transactionBoundTable = new this.db.Table(tableName, tableSchema, this);
          transactionBoundTable.core = this.db.core.table(tableName);
          memoizedTables[tableName] = transactionBoundTable;
          return transactionBoundTable;
        }
      };
      getMaxKey = (IdbKeyRange) => {
        try {
          IdbKeyRange.only([[]]);
          getMaxKey = () => [[]];
          return [[]];
        } catch (e) {
          getMaxKey = () => maxString;
          return maxString;
        }
      };
      _id_counter = 0;
      Version = class {
        _parseStoresSpec(stores, outSchema) {
          keys(stores).forEach((tableName) => {
            if (stores[tableName] !== null) {
              var indexes = parseIndexSyntax(stores[tableName]);
              var primKey = indexes.shift();
              if (primKey.multi)
                throw new exceptions.Schema("Primary key cannot be multi-valued");
              indexes.forEach((idx) => {
                if (idx.auto)
                  throw new exceptions.Schema("Only primary key can be marked as autoIncrement (++)");
                if (!idx.keyPath)
                  throw new exceptions.Schema("Index must have a name and cannot be an empty string");
              });
              outSchema[tableName] = createTableSchema(tableName, primKey, indexes);
            }
          });
        }
        stores(stores) {
          const db = this.db;
          this._cfg.storesSource = this._cfg.storesSource ? extend(this._cfg.storesSource, stores) : stores;
          const versions = db._versions;
          const storesSpec = {};
          let dbschema = {};
          versions.forEach((version) => {
            extend(storesSpec, version._cfg.storesSource);
            dbschema = version._cfg.dbschema = {};
            version._parseStoresSpec(storesSpec, dbschema);
          });
          db._dbSchema = dbschema;
          removeTablesApi(db, [db._allTables, db, db.Transaction.prototype]);
          setApiOnPlace(db, [db._allTables, db, db.Transaction.prototype, this._cfg.tables], keys(dbschema), dbschema);
          db._storeNames = keys(dbschema);
          return this;
        }
        upgrade(upgradeFunction) {
          this._cfg.contentUpgrade = promisableChain(this._cfg.contentUpgrade || nop, upgradeFunction);
          return this;
        }
      };
      virtualIndexMiddleware = {
        stack: "dbcore",
        name: "VirtualIndexMiddleware",
        level: 1,
        create: createVirtualIndexMiddleware
      };
      hooksMiddleware = {
        stack: "dbcore",
        name: "HooksMiddleware",
        level: 2,
        create: (downCore) => ({
          ...downCore,
          table(tableName) {
            const downTable = downCore.table(tableName);
            const { primaryKey } = downTable.schema;
            const tableMiddleware = {
              ...downTable,
              mutate(req) {
                const dxTrans = PSD.trans;
                const { deleting, creating, updating } = dxTrans.table(tableName).hook;
                switch (req.type) {
                  case "add":
                    if (creating.fire === nop)
                      break;
                    return dxTrans._promise("readwrite", () => addPutOrDelete(req), true);
                  case "put":
                    if (creating.fire === nop && updating.fire === nop)
                      break;
                    return dxTrans._promise("readwrite", () => addPutOrDelete(req), true);
                  case "delete":
                    if (deleting.fire === nop)
                      break;
                    return dxTrans._promise("readwrite", () => addPutOrDelete(req), true);
                  case "deleteRange":
                    if (deleting.fire === nop)
                      break;
                    return dxTrans._promise("readwrite", () => deleteRange(req), true);
                }
                return downTable.mutate(req);
                function addPutOrDelete(req2) {
                  const dxTrans2 = PSD.trans;
                  const keys2 = req2.keys || getEffectiveKeys(primaryKey, req2);
                  if (!keys2)
                    throw new Error("Keys missing");
                  req2 = req2.type === "add" || req2.type === "put" ? { ...req2, keys: keys2 } : { ...req2 };
                  if (req2.type !== "delete")
                    req2.values = [...req2.values];
                  if (req2.keys)
                    req2.keys = [...req2.keys];
                  return getExistingValues(downTable, req2, keys2).then((existingValues) => {
                    const contexts = keys2.map((key, i) => {
                      const existingValue = existingValues[i];
                      const ctx = { onerror: null, onsuccess: null };
                      if (req2.type === "delete") {
                        deleting.fire.call(ctx, key, existingValue, dxTrans2);
                      } else if (req2.type === "add" || existingValue === void 0) {
                        const generatedPrimaryKey = creating.fire.call(ctx, key, req2.values[i], dxTrans2);
                        if (key == null && generatedPrimaryKey != null) {
                          key = generatedPrimaryKey;
                          req2.keys[i] = key;
                          if (!primaryKey.outbound) {
                            setByKeyPath(req2.values[i], primaryKey.keyPath, key);
                          }
                        }
                      } else {
                        const objectDiff = getObjectDiff(existingValue, req2.values[i]);
                        const additionalChanges = updating.fire.call(ctx, objectDiff, key, existingValue, dxTrans2);
                        if (additionalChanges) {
                          const requestedValue = req2.values[i];
                          Object.keys(additionalChanges).forEach((keyPath) => {
                            if (hasOwn(requestedValue, keyPath)) {
                              requestedValue[keyPath] = additionalChanges[keyPath];
                            } else {
                              setByKeyPath(requestedValue, keyPath, additionalChanges[keyPath]);
                            }
                          });
                        }
                      }
                      return ctx;
                    });
                    return downTable.mutate(req2).then(({ failures, results, numFailures, lastResult }) => {
                      for (let i = 0; i < keys2.length; ++i) {
                        const primKey = results ? results[i] : keys2[i];
                        const ctx = contexts[i];
                        if (primKey == null) {
                          ctx.onerror && ctx.onerror(failures[i]);
                        } else {
                          ctx.onsuccess && ctx.onsuccess(
                            req2.type === "put" && existingValues[i] ? req2.values[i] : primKey
                          );
                        }
                      }
                      return { failures, results, numFailures, lastResult };
                    }).catch((error) => {
                      contexts.forEach((ctx) => ctx.onerror && ctx.onerror(error));
                      return Promise.reject(error);
                    });
                  });
                }
                function deleteRange(req2) {
                  return deleteNextChunk(req2.trans, req2.range, 1e4);
                }
                function deleteNextChunk(trans, range, limit) {
                  return downTable.query({ trans, values: false, query: { index: primaryKey, range }, limit }).then(({ result }) => {
                    return addPutOrDelete({ type: "delete", keys: result, trans }).then((res) => {
                      if (res.numFailures > 0)
                        return Promise.reject(res.failures[0]);
                      if (result.length < limit) {
                        return { failures: [], numFailures: 0, lastResult: void 0 };
                      } else {
                        return deleteNextChunk(trans, { ...range, lower: result[result.length - 1], lowerOpen: true }, limit);
                      }
                    });
                  });
                }
              }
            };
            return tableMiddleware;
          }
        })
      };
      cacheExistingValuesMiddleware = {
        stack: "dbcore",
        level: -1,
        create: (core) => {
          return {
            table: (tableName) => {
              const table = core.table(tableName);
              return {
                ...table,
                getMany: (req) => {
                  if (!req.cache) {
                    return table.getMany(req);
                  }
                  const cachedResult = getFromTransactionCache(req.keys, req.trans["_cache"], req.cache === "clone");
                  if (cachedResult) {
                    return DexiePromise.resolve(cachedResult);
                  }
                  return table.getMany(req).then((res) => {
                    req.trans["_cache"] = {
                      keys: req.keys,
                      values: req.cache === "clone" ? deepClone(res) : res
                    };
                    return res;
                  });
                },
                mutate: (req) => {
                  if (req.type !== "add")
                    req.trans["_cache"] = null;
                  return table.mutate(req);
                }
              };
            }
          };
        }
      };
      RangeSet = function(fromOrTree, to) {
        if (this) {
          extend(this, arguments.length ? { d: 1, from: fromOrTree, to: arguments.length > 1 ? to : fromOrTree } : { d: 0 });
        } else {
          const rv = new RangeSet();
          if (fromOrTree && "d" in fromOrTree) {
            extend(rv, fromOrTree);
          }
          return rv;
        }
      };
      props(RangeSet.prototype, {
        add(rangeSet) {
          mergeRanges(this, rangeSet);
          return this;
        },
        addKey(key) {
          addRange(this, key, key);
          return this;
        },
        addKeys(keys2) {
          keys2.forEach((key) => addRange(this, key, key));
          return this;
        },
        [iteratorSymbol]() {
          return getRangeSetIterator(this);
        }
      });
      observabilityMiddleware = {
        stack: "dbcore",
        level: 0,
        create: (core) => {
          const dbName = core.schema.name;
          const FULL_RANGE = new RangeSet(core.MIN_KEY, core.MAX_KEY);
          return {
            ...core,
            table: (tableName) => {
              const table = core.table(tableName);
              const { schema } = table;
              const { primaryKey } = schema;
              const { extractKey, outbound } = primaryKey;
              const tableClone = {
                ...table,
                mutate: (req) => {
                  const trans = req.trans;
                  const mutatedParts = trans.mutatedParts || (trans.mutatedParts = {});
                  const getRangeSet = (indexName) => {
                    const part = `idb://${dbName}/${tableName}/${indexName}`;
                    return mutatedParts[part] || (mutatedParts[part] = new RangeSet());
                  };
                  const pkRangeSet = getRangeSet("");
                  const delsRangeSet = getRangeSet(":dels");
                  const { type: type2 } = req;
                  let [keys2, newObjs] = req.type === "deleteRange" ? [req.range] : req.type === "delete" ? [req.keys] : req.values.length < 50 ? [[], req.values] : [];
                  const oldCache = req.trans["_cache"];
                  return table.mutate(req).then((res) => {
                    if (isArray(keys2)) {
                      if (type2 !== "delete")
                        keys2 = res.results;
                      pkRangeSet.addKeys(keys2);
                      const oldObjs = getFromTransactionCache(keys2, oldCache);
                      if (!oldObjs && type2 !== "add") {
                        delsRangeSet.addKeys(keys2);
                      }
                      if (oldObjs || newObjs) {
                        trackAffectedIndexes(getRangeSet, schema, oldObjs, newObjs);
                      }
                    } else if (keys2) {
                      const range = { from: keys2.lower, to: keys2.upper };
                      delsRangeSet.add(range);
                      pkRangeSet.add(range);
                    } else {
                      pkRangeSet.add(FULL_RANGE);
                      delsRangeSet.add(FULL_RANGE);
                      schema.indexes.forEach((idx) => getRangeSet(idx.name).add(FULL_RANGE));
                    }
                    return res;
                  });
                }
              };
              const getRange = ({ query: { index, range } }) => {
                var _a, _b;
                return [
                  index,
                  new RangeSet((_a = range.lower) !== null && _a !== void 0 ? _a : core.MIN_KEY, (_b = range.upper) !== null && _b !== void 0 ? _b : core.MAX_KEY)
                ];
              };
              const readSubscribers = {
                get: (req) => [primaryKey, new RangeSet(req.key)],
                getMany: (req) => [primaryKey, new RangeSet().addKeys(req.keys)],
                count: getRange,
                query: getRange,
                openCursor: getRange
              };
              keys(readSubscribers).forEach((method) => {
                tableClone[method] = function(req) {
                  const { subscr } = PSD;
                  if (subscr) {
                    const getRangeSet = (indexName) => {
                      const part = `idb://${dbName}/${tableName}/${indexName}`;
                      return subscr[part] || (subscr[part] = new RangeSet());
                    };
                    const pkRangeSet = getRangeSet("");
                    const delsRangeSet = getRangeSet(":dels");
                    const [queriedIndex, queriedRanges] = readSubscribers[method](req);
                    getRangeSet(queriedIndex.name || "").add(queriedRanges);
                    if (!queriedIndex.isPrimaryKey) {
                      if (method === "count") {
                        delsRangeSet.add(FULL_RANGE);
                      } else {
                        const keysPromise = method === "query" && outbound && req.values && table.query({
                          ...req,
                          values: false
                        });
                        return table[method].apply(this, arguments).then((res) => {
                          if (method === "query") {
                            if (outbound && req.values) {
                              return keysPromise.then(({ result: resultingKeys }) => {
                                pkRangeSet.addKeys(resultingKeys);
                                return res;
                              });
                            }
                            const pKeys = req.values ? res.result.map(extractKey) : res.result;
                            if (req.values) {
                              pkRangeSet.addKeys(pKeys);
                            } else {
                              delsRangeSet.addKeys(pKeys);
                            }
                          } else if (method === "openCursor") {
                            const cursor = res;
                            const wantValues = req.values;
                            return cursor && Object.create(cursor, {
                              key: {
                                get() {
                                  delsRangeSet.addKey(cursor.primaryKey);
                                  return cursor.key;
                                }
                              },
                              primaryKey: {
                                get() {
                                  const pkey = cursor.primaryKey;
                                  delsRangeSet.addKey(pkey);
                                  return pkey;
                                }
                              },
                              value: {
                                get() {
                                  wantValues && pkRangeSet.addKey(cursor.primaryKey);
                                  return cursor.value;
                                }
                              }
                            });
                          }
                          return res;
                        });
                      }
                    }
                  }
                  return table[method].apply(this, arguments);
                };
              });
              return tableClone;
            }
          };
        }
      };
      Dexie$1 = class _Dexie$1 {
        constructor(name, options) {
          this._middlewares = {};
          this.verno = 0;
          const deps = _Dexie$1.dependencies;
          this._options = options = {
            addons: _Dexie$1.addons,
            autoOpen: true,
            indexedDB: deps.indexedDB,
            IDBKeyRange: deps.IDBKeyRange,
            ...options
          };
          this._deps = {
            indexedDB: options.indexedDB,
            IDBKeyRange: options.IDBKeyRange
          };
          const { addons } = options;
          this._dbSchema = {};
          this._versions = [];
          this._storeNames = [];
          this._allTables = {};
          this.idbdb = null;
          this._novip = this;
          const state2 = {
            dbOpenError: null,
            isBeingOpened: false,
            onReadyBeingFired: null,
            openComplete: false,
            dbReadyResolve: nop,
            dbReadyPromise: null,
            cancelOpen: nop,
            openCanceller: null,
            autoSchema: true,
            PR1398_maxLoop: 3
          };
          state2.dbReadyPromise = new DexiePromise((resolve) => {
            state2.dbReadyResolve = resolve;
          });
          state2.openCanceller = new DexiePromise((_, reject) => {
            state2.cancelOpen = reject;
          });
          this._state = state2;
          this.name = name;
          this.on = Events(this, "populate", "blocked", "versionchange", "close", { ready: [promisableChain, nop] });
          this.on.ready.subscribe = override(this.on.ready.subscribe, (subscribe) => {
            return (subscriber, bSticky) => {
              _Dexie$1.vip(() => {
                const state3 = this._state;
                if (state3.openComplete) {
                  if (!state3.dbOpenError)
                    DexiePromise.resolve().then(subscriber);
                  if (bSticky)
                    subscribe(subscriber);
                } else if (state3.onReadyBeingFired) {
                  state3.onReadyBeingFired.push(subscriber);
                  if (bSticky)
                    subscribe(subscriber);
                } else {
                  subscribe(subscriber);
                  const db = this;
                  if (!bSticky)
                    subscribe(function unsubscribe() {
                      db.on.ready.unsubscribe(subscriber);
                      db.on.ready.unsubscribe(unsubscribe);
                    });
                }
              });
            };
          });
          this.Collection = createCollectionConstructor(this);
          this.Table = createTableConstructor(this);
          this.Transaction = createTransactionConstructor(this);
          this.Version = createVersionConstructor(this);
          this.WhereClause = createWhereClauseConstructor(this);
          this.on("versionchange", (ev) => {
            if (ev.newVersion > 0)
              console.warn(`Another connection wants to upgrade database '${this.name}'. Closing db now to resume the upgrade.`);
            else
              console.warn(`Another connection wants to delete database '${this.name}'. Closing db now to resume the delete request.`);
            this.close();
          });
          this.on("blocked", (ev) => {
            if (!ev.newVersion || ev.newVersion < ev.oldVersion)
              console.warn(`Dexie.delete('${this.name}') was blocked`);
            else
              console.warn(`Upgrade '${this.name}' blocked by other connection holding version ${ev.oldVersion / 10}`);
          });
          this._maxKey = getMaxKey(options.IDBKeyRange);
          this._createTransaction = (mode, storeNames, dbschema, parentTransaction) => new this.Transaction(mode, storeNames, dbschema, this._options.chromeTransactionDurability, parentTransaction);
          this._fireOnBlocked = (ev) => {
            this.on("blocked").fire(ev);
            connections.filter((c) => c.name === this.name && c !== this && !c._state.vcFired).map((c) => c.on("versionchange").fire(ev));
          };
          this.use(virtualIndexMiddleware);
          this.use(hooksMiddleware);
          this.use(observabilityMiddleware);
          this.use(cacheExistingValuesMiddleware);
          this.vip = Object.create(this, { _vip: { value: true } });
          addons.forEach((addon) => addon(this));
        }
        version(versionNumber) {
          if (isNaN(versionNumber) || versionNumber < 0.1)
            throw new exceptions.Type(`Given version is not a positive number`);
          versionNumber = Math.round(versionNumber * 10) / 10;
          if (this.idbdb || this._state.isBeingOpened)
            throw new exceptions.Schema("Cannot add version when database is open");
          this.verno = Math.max(this.verno, versionNumber);
          const versions = this._versions;
          var versionInstance = versions.filter((v) => v._cfg.version === versionNumber)[0];
          if (versionInstance)
            return versionInstance;
          versionInstance = new this.Version(versionNumber);
          versions.push(versionInstance);
          versions.sort(lowerVersionFirst);
          versionInstance.stores({});
          this._state.autoSchema = false;
          return versionInstance;
        }
        _whenReady(fn) {
          return this.idbdb && (this._state.openComplete || PSD.letThrough || this._vip) ? fn() : new DexiePromise((resolve, reject) => {
            if (this._state.openComplete) {
              return reject(new exceptions.DatabaseClosed(this._state.dbOpenError));
            }
            if (!this._state.isBeingOpened) {
              if (!this._options.autoOpen) {
                reject(new exceptions.DatabaseClosed());
                return;
              }
              this.open().catch(nop);
            }
            this._state.dbReadyPromise.then(resolve, reject);
          }).then(fn);
        }
        use({ stack, create, level, name }) {
          if (name)
            this.unuse({ stack, name });
          const middlewares = this._middlewares[stack] || (this._middlewares[stack] = []);
          middlewares.push({ stack, create, level: level == null ? 10 : level, name });
          middlewares.sort((a, b) => a.level - b.level);
          return this;
        }
        unuse({ stack, name, create }) {
          if (stack && this._middlewares[stack]) {
            this._middlewares[stack] = this._middlewares[stack].filter((mw) => create ? mw.create !== create : name ? mw.name !== name : false);
          }
          return this;
        }
        open() {
          return dexieOpen(this);
        }
        _close() {
          const state2 = this._state;
          const idx = connections.indexOf(this);
          if (idx >= 0)
            connections.splice(idx, 1);
          if (this.idbdb) {
            try {
              this.idbdb.close();
            } catch (e) {
            }
            this._novip.idbdb = null;
          }
          state2.dbReadyPromise = new DexiePromise((resolve) => {
            state2.dbReadyResolve = resolve;
          });
          state2.openCanceller = new DexiePromise((_, reject) => {
            state2.cancelOpen = reject;
          });
        }
        close() {
          this._close();
          const state2 = this._state;
          this._options.autoOpen = false;
          state2.dbOpenError = new exceptions.DatabaseClosed();
          if (state2.isBeingOpened)
            state2.cancelOpen(state2.dbOpenError);
        }
        delete() {
          const hasArguments = arguments.length > 0;
          const state2 = this._state;
          return new DexiePromise((resolve, reject) => {
            const doDelete = () => {
              this.close();
              var req = this._deps.indexedDB.deleteDatabase(this.name);
              req.onsuccess = wrap(() => {
                _onDatabaseDeleted(this._deps, this.name);
                resolve();
              });
              req.onerror = eventRejectHandler(reject);
              req.onblocked = this._fireOnBlocked;
            };
            if (hasArguments)
              throw new exceptions.InvalidArgument("Arguments not allowed in db.delete()");
            if (state2.isBeingOpened) {
              state2.dbReadyPromise.then(doDelete);
            } else {
              doDelete();
            }
          });
        }
        backendDB() {
          return this.idbdb;
        }
        isOpen() {
          return this.idbdb !== null;
        }
        hasBeenClosed() {
          const dbOpenError = this._state.dbOpenError;
          return dbOpenError && dbOpenError.name === "DatabaseClosed";
        }
        hasFailed() {
          return this._state.dbOpenError !== null;
        }
        dynamicallyOpened() {
          return this._state.autoSchema;
        }
        get tables() {
          return keys(this._allTables).map((name) => this._allTables[name]);
        }
        transaction() {
          const args = extractTransactionArgs.apply(this, arguments);
          return this._transaction.apply(this, args);
        }
        _transaction(mode, tables, scopeFunc) {
          let parentTransaction = PSD.trans;
          if (!parentTransaction || parentTransaction.db !== this || mode.indexOf("!") !== -1)
            parentTransaction = null;
          const onlyIfCompatible = mode.indexOf("?") !== -1;
          mode = mode.replace("!", "").replace("?", "");
          let idbMode, storeNames;
          try {
            storeNames = tables.map((table) => {
              var storeName = table instanceof this.Table ? table.name : table;
              if (typeof storeName !== "string")
                throw new TypeError("Invalid table argument to Dexie.transaction(). Only Table or String are allowed");
              return storeName;
            });
            if (mode == "r" || mode === READONLY)
              idbMode = READONLY;
            else if (mode == "rw" || mode == READWRITE)
              idbMode = READWRITE;
            else
              throw new exceptions.InvalidArgument("Invalid transaction mode: " + mode);
            if (parentTransaction) {
              if (parentTransaction.mode === READONLY && idbMode === READWRITE) {
                if (onlyIfCompatible) {
                  parentTransaction = null;
                } else
                  throw new exceptions.SubTransaction("Cannot enter a sub-transaction with READWRITE mode when parent transaction is READONLY");
              }
              if (parentTransaction) {
                storeNames.forEach((storeName) => {
                  if (parentTransaction && parentTransaction.storeNames.indexOf(storeName) === -1) {
                    if (onlyIfCompatible) {
                      parentTransaction = null;
                    } else
                      throw new exceptions.SubTransaction("Table " + storeName + " not included in parent transaction.");
                  }
                });
              }
              if (onlyIfCompatible && parentTransaction && !parentTransaction.active) {
                parentTransaction = null;
              }
            }
          } catch (e) {
            return parentTransaction ? parentTransaction._promise(null, (_, reject) => {
              reject(e);
            }) : rejection(e);
          }
          const enterTransaction = enterTransactionScope.bind(null, this, idbMode, storeNames, parentTransaction, scopeFunc);
          return parentTransaction ? parentTransaction._promise(idbMode, enterTransaction, "lock") : PSD.trans ? usePSD(PSD.transless, () => this._whenReady(enterTransaction)) : this._whenReady(enterTransaction);
        }
        table(tableName) {
          if (!hasOwn(this._allTables, tableName)) {
            throw new exceptions.InvalidTable(`Table ${tableName} does not exist`);
          }
          return this._allTables[tableName];
        }
      };
      symbolObservable = typeof Symbol !== "undefined" && "observable" in Symbol ? Symbol.observable : "@@observable";
      Observable = class {
        constructor(subscribe) {
          this._subscribe = subscribe;
        }
        subscribe(x, error, complete) {
          return this._subscribe(!x || typeof x === "function" ? { next: x, error, complete } : x);
        }
        [symbolObservable]() {
          return this;
        }
      };
      try {
        domDeps = {
          indexedDB: _global.indexedDB || _global.mozIndexedDB || _global.webkitIndexedDB || _global.msIndexedDB,
          IDBKeyRange: _global.IDBKeyRange || _global.webkitIDBKeyRange
        };
      } catch (e) {
        domDeps = { indexedDB: null, IDBKeyRange: null };
      }
      Dexie = Dexie$1;
      props(Dexie, {
        ...fullNameExceptions,
        delete(databaseName) {
          const db = new Dexie(databaseName, { addons: [] });
          return db.delete();
        },
        exists(name) {
          return new Dexie(name, { addons: [] }).open().then((db) => {
            db.close();
            return true;
          }).catch("NoSuchDatabaseError", () => false);
        },
        getDatabaseNames(cb) {
          try {
            return getDatabaseNames(Dexie.dependencies).then(cb);
          } catch (_a) {
            return rejection(new exceptions.MissingAPI());
          }
        },
        defineClass() {
          function Class(content) {
            extend(this, content);
          }
          return Class;
        },
        ignoreTransaction(scopeFunc) {
          return PSD.trans ? usePSD(PSD.transless, scopeFunc) : scopeFunc();
        },
        vip,
        async: function(generatorFn) {
          return function() {
            try {
              var rv = awaitIterator(generatorFn.apply(this, arguments));
              if (!rv || typeof rv.then !== "function")
                return DexiePromise.resolve(rv);
              return rv;
            } catch (e) {
              return rejection(e);
            }
          };
        },
        spawn: function(generatorFn, args, thiz) {
          try {
            var rv = awaitIterator(generatorFn.apply(thiz, args || []));
            if (!rv || typeof rv.then !== "function")
              return DexiePromise.resolve(rv);
            return rv;
          } catch (e) {
            return rejection(e);
          }
        },
        currentTransaction: {
          get: () => PSD.trans || null
        },
        waitFor: function(promiseOrFunction, optionalTimeout) {
          const promise = DexiePromise.resolve(typeof promiseOrFunction === "function" ? Dexie.ignoreTransaction(promiseOrFunction) : promiseOrFunction).timeout(optionalTimeout || 6e4);
          return PSD.trans ? PSD.trans.waitFor(promise) : promise;
        },
        Promise: DexiePromise,
        debug: {
          get: () => debug,
          set: (value) => {
            setDebug(value, value === "dexie" ? () => true : dexieStackFrameFilter);
          }
        },
        derive,
        extend,
        props,
        override,
        Events,
        on: globalEvents,
        liveQuery,
        extendObservabilitySet,
        getByKeyPath,
        setByKeyPath,
        delByKeyPath,
        shallowClone,
        deepClone,
        getObjectDiff,
        cmp,
        asap: asap$1,
        minKey,
        addons: [],
        connections,
        errnames,
        dependencies: domDeps,
        semVer: DEXIE_VERSION,
        version: DEXIE_VERSION.split(".").map((n) => parseInt(n)).reduce((p, c, i) => p + c / Math.pow(10, i * 2))
      });
      Dexie.maxKey = getMaxKey(Dexie.dependencies.IDBKeyRange);
      if (typeof dispatchEvent !== "undefined" && typeof addEventListener !== "undefined") {
        globalEvents(DEXIE_STORAGE_MUTATED_EVENT_NAME, (updatedParts) => {
          if (!propagatingLocally) {
            let event;
            if (isIEOrEdge) {
              event = document.createEvent("CustomEvent");
              event.initCustomEvent(STORAGE_MUTATED_DOM_EVENT_NAME, true, true, updatedParts);
            } else {
              event = new CustomEvent(STORAGE_MUTATED_DOM_EVENT_NAME, {
                detail: updatedParts
              });
            }
            propagatingLocally = true;
            dispatchEvent(event);
            propagatingLocally = false;
          }
        });
        addEventListener(STORAGE_MUTATED_DOM_EVENT_NAME, ({ detail }) => {
          if (!propagatingLocally) {
            propagateLocally(detail);
          }
        });
      }
      propagatingLocally = false;
      if (typeof BroadcastChannel !== "undefined") {
        const bc = new BroadcastChannel(STORAGE_MUTATED_DOM_EVENT_NAME);
        if (typeof bc.unref === "function") {
          bc.unref();
        }
        globalEvents(DEXIE_STORAGE_MUTATED_EVENT_NAME, (changedParts) => {
          if (!propagatingLocally) {
            bc.postMessage(changedParts);
          }
        });
        bc.onmessage = (ev) => {
          if (ev.data)
            propagateLocally(ev.data);
        };
      } else if (typeof self !== "undefined" && typeof navigator !== "undefined") {
        globalEvents(DEXIE_STORAGE_MUTATED_EVENT_NAME, (changedParts) => {
          try {
            if (!propagatingLocally) {
              if (typeof localStorage !== "undefined") {
                localStorage.setItem(STORAGE_MUTATED_DOM_EVENT_NAME, JSON.stringify({
                  trig: Math.random(),
                  changedParts
                }));
              }
              if (typeof self["clients"] === "object") {
                [...self["clients"].matchAll({ includeUncontrolled: true })].forEach((client) => client.postMessage({
                  type: STORAGE_MUTATED_DOM_EVENT_NAME,
                  changedParts
                }));
              }
            }
          } catch (_a) {
          }
        });
        if (typeof addEventListener !== "undefined") {
          addEventListener("storage", (ev) => {
            if (ev.key === STORAGE_MUTATED_DOM_EVENT_NAME) {
              const data = JSON.parse(ev.newValue);
              if (data)
                propagateLocally(data.changedParts);
            }
          });
        }
        const swContainer = self.document && navigator.serviceWorker;
        if (swContainer) {
          swContainer.addEventListener("message", propagateMessageLocally);
        }
      }
      DexiePromise.rejectionMapper = mapError;
      setDebug(debug, dexieStackFrameFilter);
    }
  });

  // src/renderer/js/storage/storage.js
  var require_storage = __commonJS({
    "src/renderer/js/storage/storage.js"(exports, module) {
      var Dexie2 = (init_dexie(), __toCommonJS(dexie_exports));
      var TimeTrackerDB = class extends Dexie2 {
        constructor() {
          super("TimeTrackerDB");
          this.version(1).stores({
            timeEntries: "id, startTime, projectId, userId",
            projects: "id, name, status",
            tasks: "id, projectId, status",
            syncQueue: "++id, type, action, data, timestamp"
          });
        }
      };
      var db = new TimeTrackerDB();
      var StorageService2 = {
        // Time Entries
        async saveTimeEntry(entry) {
          return await db.timeEntries.put(entry);
        },
        async getTimeEntries(filters = {}) {
          let collection = db.timeEntries.toCollection();
          if (filters.startDate) {
            collection = collection.filter((entry) => entry.startTime >= filters.startDate);
          }
          if (filters.endDate) {
            collection = collection.filter((entry) => entry.startTime <= filters.endDate);
          }
          if (filters.projectId) {
            collection = collection.filter((entry) => entry.projectId === filters.projectId);
          }
          return await collection.toArray();
        },
        async deleteTimeEntry(id) {
          return await db.timeEntries.delete(id);
        },
        // Projects
        async saveProject(project) {
          return await db.projects.put(project);
        },
        async getProjects(filters = {}) {
          let collection = db.projects.toCollection();
          if (filters.status) {
            collection = collection.filter((project) => project.status === filters.status);
          }
          return await collection.toArray();
        },
        async deleteProject(id) {
          return await db.projects.delete(id);
        },
        // Tasks
        async saveTask(task2) {
          return await db.tasks.put(task2);
        },
        async getTasks(filters = {}) {
          let collection = db.tasks.toCollection();
          if (filters.projectId) {
            collection = collection.filter((task2) => task2.projectId === filters.projectId);
          }
          if (filters.status) {
            collection = collection.filter((task2) => task2.status === filters.status);
          }
          return await collection.toArray();
        },
        // Sync Queue
        async addToSyncQueue(type2, action, data) {
          return await db.syncQueue.add({
            type: type2,
            // 'time_entry', 'project', etc.
            action,
            // 'create', 'update', 'delete'
            data,
            timestamp: /* @__PURE__ */ new Date()
          });
        },
        async getSyncQueue() {
          return await db.syncQueue.toArray();
        },
        async removeFromSyncQueue(id) {
          return await db.syncQueue.delete(id);
        },
        async clearSyncQueue() {
          return await db.syncQueue.clear();
        },
        // Clear all data
        async clearAll() {
          await db.timeEntries.clear();
          await db.projects.clear();
          await db.tasks.clear();
          await db.syncQueue.clear();
        }
      };
      if (typeof module !== "undefined" && module.exports) {
        module.exports = StorageService2;
      }
      if (typeof window !== "undefined") {
        window.StorageService = StorageService2;
      }
    }
  });

  // src/renderer/js/ui/notifications.js
  var require_notifications = __commonJS({
    "src/renderer/js/ui/notifications.js"(exports, module) {
      function showError2(message) {
        let errorDiv = document.getElementById("error-notification");
        if (!errorDiv) {
          errorDiv = document.createElement("div");
          errorDiv.id = "error-notification";
          errorDiv.className = "notification notification-error";
          errorDiv.setAttribute("role", "alert");
          errorDiv.setAttribute("aria-live", "assertive");
          document.body.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
        errorDiv.style.display = "block";
        setTimeout(() => {
          errorDiv.style.display = "none";
        }, 5e3);
      }
      function showSuccess2(message) {
        let successDiv = document.getElementById("success-notification");
        if (!successDiv) {
          successDiv = document.createElement("div");
          successDiv.id = "success-notification";
          successDiv.className = "notification notification-success";
          successDiv.setAttribute("role", "status");
          successDiv.setAttribute("aria-live", "polite");
          document.body.appendChild(successDiv);
        }
        successDiv.textContent = message;
        successDiv.style.display = "block";
        setTimeout(() => {
          successDiv.style.display = "none";
        }, 3e3);
      }
      if (typeof module !== "undefined" && module.exports) {
        module.exports = { showError: showError2, showSuccess: showSuccess2 };
      }
    }
  });

  // src/renderer/js/state.js
  var require_state = __commonJS({
    "src/renderer/js/state.js"(exports, module) {
      module.exports = {
        apiClient: null,
        currentView: "dashboard",
        timerInterval: null,
        isTimerRunning: false,
        connectionCheckInterval: null,
        currentUserProfile: { is_admin: false, can_approve: false },
        cachedInvoices: [],
        cachedExpenses: [],
        cachedWorkforce: { periods: [], capacity: [], timeOffRequests: [], balances: [] },
        viewFilters: { invoiceQuery: "", expenseQuery: "", timeoffQuery: "" },
        viewLimits: { invoices: 20, expenses: 20, timeoff: 20 },
        pagination: {
          invoices: { page: 1, perPage: 20, totalPages: 1, total: 0 },
          expenses: { page: 1, perPage: 20, totalPages: 1, total: 0 }
        }
      };
    }
  });

  // src/renderer/js/app.js
  var { storeGet, storeSet, storeDelete, storeClear } = window.config || {};
  var ApiClient = require_client();
  var StorageService = require_storage();
  var { showError, showSuccess } = require_notifications();
  var state = require_state();
  async function initApp() {
    const serverUrl = await storeGet("server_url");
    const apiToken = await storeGet("api_token");
    if (serverUrl && apiToken) {
      state.apiClient = new ApiClient(serverUrl);
      await state.apiClient.setAuthToken(apiToken);
      const isValid = await state.apiClient.validateToken();
      if (isValid) {
        await loadCurrentUserProfile();
        showMainScreen();
        loadDashboard();
      } else {
        showLoginScreen();
      }
    } else {
      showLoginScreen();
    }
    setupEventListeners();
    startConnectionCheck();
    setupTrayListeners();
  }
  function setupTrayListeners() {
    if (window.electronAPI && window.electronAPI.onTrayAction) {
      window.electronAPI.onTrayAction((action) => {
        if (action === "start-timer" && !state.isTimerRunning) {
          handleStartTimer();
        } else if (action === "stop-timer" && state.isTimerRunning) {
          handleStopTimer();
        }
      });
    }
  }
  function startConnectionCheck() {
    state.connectionCheckInterval = setInterval(async () => {
      await checkConnection();
    }, 3e4);
    checkConnection();
  }
  async function checkConnection() {
    if (!state.apiClient) {
      updateConnectionStatus("disconnected");
      return;
    }
    try {
      const isValid = await state.apiClient.validateToken();
      updateConnectionStatus(isValid ? "connected" : "error");
    } catch (error) {
      updateConnectionStatus("error");
    }
  }
  async function loadCurrentUserProfile() {
    if (!state.apiClient) return;
    try {
      const me = await state.apiClient.getUsersMe();
      const user = me.user || {};
      const role = String(user.role || "").toLowerCase();
      const roleCanApprove = ["admin", "owner", "manager", "approver"].includes(role);
      state.currentUserProfile = {
        is_admin: Boolean(user.is_admin),
        can_approve: Boolean(user.is_admin) || roleCanApprove
      };
    } catch (_) {
      state.currentUserProfile = { is_admin: false, can_approve: false };
    }
  }
  function updateConnectionStatus(status) {
    const statusEl = document.getElementById("connection-status");
    if (!statusEl) return;
    statusEl.className = "connection-status connection-" + status;
    var label = "Connection status: ";
    switch (status) {
      case "connected":
        statusEl.textContent = "\u25CF";
        statusEl.title = "Connected";
        label += "Connected";
        break;
      case "error":
        statusEl.textContent = "\u25CF";
        statusEl.title = "Connection error";
        label += "Error";
        break;
      case "disconnected":
        statusEl.textContent = "\u25CB";
        statusEl.title = "Disconnected";
        label += "Disconnected";
        break;
      default:
        label += "Unknown";
    }
    statusEl.setAttribute("aria-label", label);
  }
  function setupEventListeners() {
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
      loginForm.addEventListener("submit", handleLogin);
    }
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const view = e.target.dataset.view;
        switchView(view);
      });
    });
    const minimizeBtn = document.getElementById("minimize-btn");
    const maximizeBtn = document.getElementById("maximize-btn");
    const closeBtn = document.getElementById("close-btn");
    if (minimizeBtn) minimizeBtn.addEventListener("click", () => window.electronAPI?.minimizeWindow());
    if (maximizeBtn) maximizeBtn.addEventListener("click", () => window.electronAPI?.maximizeWindow());
    if (closeBtn) closeBtn.addEventListener("click", () => window.electronAPI?.closeWindow());
    const startTimerBtn = document.getElementById("start-timer-btn");
    const stopTimerBtn = document.getElementById("stop-timer-btn");
    if (startTimerBtn) startTimerBtn.addEventListener("click", handleStartTimer);
    if (stopTimerBtn) stopTimerBtn.addEventListener("click", handleStopTimer);
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);
    const saveSettingsBtn = document.getElementById("save-settings-btn");
    const testConnectionBtn = document.getElementById("test-connection-btn");
    const autoSyncInput = document.getElementById("auto-sync");
    if (saveSettingsBtn) saveSettingsBtn.addEventListener("click", handleSaveSettings);
    if (testConnectionBtn) testConnectionBtn.addEventListener("click", handleTestConnection);
    if (autoSyncInput) {
      autoSyncInput.addEventListener("change", () => updateSyncIntervalState());
    }
    const addEntryBtn = document.getElementById("add-entry-btn");
    const filterEntriesBtn = document.getElementById("filter-entries-btn");
    const applyFilterBtn = document.getElementById("apply-filter-btn");
    const clearFilterBtn = document.getElementById("clear-filter-btn");
    const addExpenseBtn = document.getElementById("add-expense-btn");
    const refreshPeriodsBtn = document.getElementById("refresh-periods-btn");
    const addInvoiceBtn = document.getElementById("add-invoice-btn");
    const addTimeoffBtn = document.getElementById("add-timeoff-btn");
    const invoiceSearchInput = document.getElementById("invoice-search");
    const expenseSearchInput = document.getElementById("expense-search");
    const timeoffSearchInput = document.getElementById("timeoff-search");
    const invoicePrevPageBtn = document.getElementById("invoice-prev-page-btn");
    const invoiceNextPageBtn = document.getElementById("invoice-next-page-btn");
    const expensePrevPageBtn = document.getElementById("expense-prev-page-btn");
    const expenseNextPageBtn = document.getElementById("expense-next-page-btn");
    if (addEntryBtn) addEntryBtn.addEventListener("click", () => showTimeEntryForm());
    if (filterEntriesBtn) filterEntriesBtn.addEventListener("click", toggleFilters);
    if (applyFilterBtn) applyFilterBtn.addEventListener("click", applyFilters);
    if (clearFilterBtn) clearFilterBtn.addEventListener("click", clearFilters);
    if (addExpenseBtn) addExpenseBtn.addEventListener("click", () => showCreateExpenseDialog());
    if (refreshPeriodsBtn) refreshPeriodsBtn.addEventListener("click", () => loadWorkforce());
    if (addInvoiceBtn) addInvoiceBtn.addEventListener("click", () => showCreateInvoiceDialog());
    if (addTimeoffBtn) addTimeoffBtn.addEventListener("click", () => showCreateTimeOffDialog());
    if (invoiceSearchInput) {
      invoiceSearchInput.addEventListener("input", (e) => {
        state.viewFilters.invoiceQuery = String(e.target.value || "").trim().toLowerCase();
        renderInvoices();
      });
    }
    if (expenseSearchInput) {
      expenseSearchInput.addEventListener("input", (e) => {
        state.viewFilters.expenseQuery = String(e.target.value || "").trim().toLowerCase();
        renderExpenses();
      });
    }
    if (timeoffSearchInput) {
      timeoffSearchInput.addEventListener("input", (e) => {
        state.viewFilters.timeoffQuery = String(e.target.value || "").trim().toLowerCase();
        renderTimeOffRequests();
      });
    }
    if (invoicePrevPageBtn) invoicePrevPageBtn.addEventListener("click", () => changeInvoicePage(-1));
    if (invoiceNextPageBtn) invoiceNextPageBtn.addEventListener("click", () => changeInvoicePage(1));
    if (expensePrevPageBtn) expensePrevPageBtn.addEventListener("click", () => changeExpensePage(-1));
    if (expenseNextPageBtn) expenseNextPageBtn.addEventListener("click", () => changeExpensePage(1));
  }
  async function handleLogin(e) {
    e.preventDefault();
    const serverUrl = document.getElementById("server-url").value.trim();
    const apiToken = document.getElementById("api-token").value.trim();
    const errorDiv = document.getElementById("login-error");
    if (!serverUrl || !isValidUrl(serverUrl)) {
      showLoginError("Please enter a valid server URL");
      return;
    }
    if (!apiToken || !apiToken.startsWith("tt_")) {
      showError("Please enter a valid API token (must start with tt_)");
      return;
    }
    await storeSet("server_url", serverUrl);
    await storeSet("api_token", apiToken);
    state.apiClient = new ApiClient(serverUrl);
    await state.apiClient.setAuthToken(apiToken);
    const isValid = await state.apiClient.validateToken();
    if (isValid) {
      await loadCurrentUserProfile();
      updateConnectionStatus("connected");
      showMainScreen();
      loadDashboard();
    } else {
      updateConnectionStatus("error");
      showLoginError("Invalid API token. Please check your token.");
      await storeDelete("api_token");
    }
  }
  function showLoginError(message) {
    const errorDiv = document.getElementById("login-error");
    if (errorDiv) {
      errorDiv.textContent = message;
      errorDiv.classList.add("show");
    }
  }
  function showLoginScreen() {
    document.getElementById("loading-screen").classList.remove("active");
    document.getElementById("login-screen").classList.add("active");
    document.getElementById("main-screen").classList.remove("active");
  }
  function showMainScreen() {
    document.getElementById("loading-screen").classList.remove("active");
    document.getElementById("login-screen").classList.remove("active");
    document.getElementById("main-screen").classList.add("active");
  }
  function switchView(view) {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.classList.remove("active");
    });
    document.querySelector(`[data-view="${view}"]`).classList.add("active");
    document.querySelectorAll(".view").forEach((v) => {
      v.classList.remove("active");
    });
    document.getElementById(`${view}-view`).classList.add("active");
    state.currentView = view;
    if (view === "dashboard") {
      loadDashboard();
    } else if (view === "projects") {
      loadProjects();
    } else if (view === "entries") {
      loadTimeEntries();
      loadProjectsForFilter();
    } else if (view === "invoices") {
      loadInvoices();
    } else if (view === "expenses") {
      loadExpenses();
    } else if (view === "workforce") {
      loadWorkforce();
    } else if (view === "settings") {
      loadSettings();
    }
  }
  async function loadDashboard() {
    if (!state.apiClient) return;
    try {
      const timerResponse = await state.apiClient.getTimerStatus();
      if (timerResponse.data.active) {
        state.isTimerRunning = true;
        updateTimerDisplay(timerResponse.data.timer);
        startTimerPolling();
      }
      const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
      const entriesResponse = await state.apiClient.getTimeEntries({ startDate: today, endDate: today });
      const totalSeconds = entriesResponse.data.time_entries?.reduce((sum, entry) => {
        return sum + (entry.duration_seconds || 0);
      }, 0) || 0;
      document.getElementById("today-summary").textContent = formatDuration(totalSeconds);
      loadRecentEntries();
    } catch (error) {
      console.error("Error loading dashboard:", error);
    }
  }
  async function loadRecentEntries() {
    if (!state.apiClient) return;
    try {
      const response = await state.apiClient.getTimeEntries({ perPage: 5 });
      const entries = response.data.time_entries || [];
      const entriesList = document.getElementById("recent-entries");
      if (entries.length === 0) {
        entriesList.innerHTML = '<p class="empty-state">No recent entries</p>';
        return;
      }
      entriesList.innerHTML = entries.map((entry) => `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${entry.project?.name || "Unknown Project"}</h3>
          <p>${formatDateTime(entry.start_time)}</p>
        </div>
        <div class="entry-time">${formatDuration(entry.duration_seconds || 0)}</div>
      </div>
    `).join("");
    } catch (error) {
      console.error("Error loading recent entries:", error);
    }
  }
  async function loadProjects() {
    if (!state.apiClient) return;
    try {
      const response = await state.apiClient.getProjects({ status: "active" });
      const projects = response.data.projects || [];
      const projectsList = document.getElementById("projects-list");
      if (projects.length === 0) {
        projectsList.innerHTML = '<p class="empty-state">No projects found</p>';
        return;
      }
      projectsList.innerHTML = projects.map((project) => `
      <div class="project-card" onclick="selectProject(${project.id})">
        <h3>${project.name}</h3>
        <p>${project.client || "No client"}</p>
      </div>
    `).join("");
    } catch (error) {
      console.error("Error loading projects:", error);
    }
  }
  var currentFilters = {
    startDate: null,
    endDate: null,
    projectId: null
  };
  async function loadTimeEntries() {
    if (!state.apiClient) return;
    try {
      const params = { perPage: 50 };
      if (currentFilters.startDate) params.startDate = currentFilters.startDate;
      if (currentFilters.endDate) params.endDate = currentFilters.endDate;
      if (currentFilters.projectId) params.projectId = currentFilters.projectId;
      const response = await state.apiClient.getTimeEntries(params);
      const entries = response.data.time_entries || [];
      const entriesList = document.getElementById("entries-list");
      if (entries.length === 0) {
        entriesList.innerHTML = '<p class="empty-state">No time entries</p>';
        return;
      }
      entriesList.innerHTML = entries.map((entry) => `
      <div class="entry-item" data-entry-id="${entry.id}">
        <div class="entry-info">
          <h3>${entry.project?.name || "Unknown Project"}</h3>
          ${entry.task ? `<p class="entry-task">${entry.task.name}</p>` : ""}
          <p class="entry-time-range">
            ${formatDateTime(entry.start_time)} - ${entry.end_time ? formatDateTime(entry.end_time) : "Running"}
          </p>
          ${entry.notes ? `<p class="entry-notes">${entry.notes}</p>` : ""}
          ${entry.tags ? `<p class="entry-tags">Tags: ${entry.tags}</p>` : ""}
          ${entry.billable ? '<span class="badge badge-success">Billable</span>' : ""}
        </div>
        <div class="entry-actions">
          <div class="entry-time">${formatDuration(entry.duration_seconds || 0)}</div>
          <button class="btn btn-sm btn-secondary" onclick="editTimeEntry(${entry.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteTimeEntry(${entry.id})">Delete</button>
        </div>
      </div>
    `).join("");
    } catch (error) {
      console.error("Error loading time entries:", error);
      showError("Failed to load time entries: " + (error.response?.data?.error || error.message));
    }
  }
  async function handleStartTimer() {
    if (!state.apiClient) return;
    const result = await showStartTimerDialog();
    if (!result) return;
    try {
      const response = await state.apiClient.startTimer({
        projectId: result.projectId,
        taskId: result.taskId,
        notes: result.notes
      });
      if (response.data && response.data.timer) {
        state.isTimerRunning = true;
        updateTimerDisplay(response.data.timer);
        startTimerPolling();
        document.getElementById("start-timer-btn").style.display = "none";
        document.getElementById("stop-timer-btn").style.display = "block";
      }
    } catch (error) {
      showError("Failed to start timer: " + (error.response?.data?.error || error.message));
    }
  }
  async function showStartTimerDialog() {
    return new Promise(async (resolve) => {
      let projects = [];
      let requirements = { require_task: false, require_description: false, description_min_length: 20 };
      try {
        const [projectsResponse, usersMeResponse] = await Promise.all([
          state.apiClient.getProjects({ status: "active" }),
          state.apiClient.getUsersMe().catch(() => ({}))
        ]);
        projects = projectsResponse.data.projects || [];
        if (usersMeResponse.time_entry_requirements) {
          requirements = usersMeResponse.time_entry_requirements;
        }
      } catch (error) {
        showError("Failed to load projects");
        resolve(null);
        return;
      }
      if (projects.length === 0) {
        showError("No active projects found");
        resolve(null);
        return;
      }
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>Start Timer</h3>
          <button class="modal-close" onclick="this.closest('.modal').remove()">\xD7</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="timer-project-select">Project *</label>
            <select id="timer-project-select" class="form-control" required>
              <option value="">Select a project...</option>
              ${projects.map((p) => `<option value="${p.id}">${p.name}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label for="timer-task-select">${requirements.require_task ? "Task *" : "Task (Optional)"}</label>
            <select id="timer-task-select" class="form-control">
              <option value="">No task</option>
            </select>
          </div>
          <div class="form-group">
            <label for="timer-notes-input">${requirements.require_description ? "Notes *" : "Notes (Optional)"}</label>
            <textarea id="timer-notes-input" class="form-control" rows="3" placeholder="What are you working on?"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="btn btn-primary" id="start-timer-confirm">Start</button>
        </div>
      </div>
    `;
      document.body.appendChild(modal);
      const projectSelect = modal.querySelector("#timer-project-select");
      const taskSelect = modal.querySelector("#timer-task-select");
      const notesInput = modal.querySelector("#timer-notes-input");
      const confirmBtn = modal.querySelector("#start-timer-confirm");
      projectSelect.addEventListener("change", async (e) => {
        const projectId = parseInt(e.target.value);
        if (!projectId) {
          taskSelect.innerHTML = '<option value="">No task</option>';
          return;
        }
        try {
          const tasksResponse = await state.apiClient.getTasks({ projectId });
          const tasks = tasksResponse.data.tasks || [];
          taskSelect.innerHTML = '<option value="">No task</option>' + tasks.map((t) => `<option value="${t.id}">${t.name}</option>`).join("");
        } catch (error) {
          console.error("Failed to load tasks:", error);
        }
      });
      confirmBtn.addEventListener("click", () => {
        const projectId = parseInt(projectSelect.value);
        if (!projectId) {
          showError("Please select a project");
          return;
        }
        const taskId = taskSelect.value ? parseInt(taskSelect.value) : null;
        if (requirements.require_task && !taskId) {
          showError("A task must be selected when logging time for a project");
          return;
        }
        const notes = notesInput.value.trim();
        if (requirements.require_description) {
          if (!notes) {
            showError("A description is required when logging time");
            return;
          }
          const minLen = requirements.description_min_length || 20;
          if (notes.length < minLen) {
            showError(`Description must be at least ${minLen} characters`);
            return;
          }
        }
        modal.remove();
        resolve({ projectId, taskId, notes: notes || null });
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.remove();
          resolve(null);
        }
      });
    });
  }
  async function handleStopTimer() {
    if (!state.apiClient) return;
    try {
      await state.apiClient.stopTimer();
      state.isTimerRunning = false;
      stopTimerPolling();
      document.getElementById("timer-display").textContent = "00:00:00";
      document.getElementById("timer-project").textContent = "No active timer";
      document.getElementById("timer-task").style.display = "none";
      document.getElementById("timer-notes").style.display = "none";
      document.getElementById("start-timer-btn").style.display = "block";
      document.getElementById("stop-timer-btn").style.display = "none";
      updateTimerDisplay(null);
      loadTimeEntries();
      loadRecentEntries();
    } catch (error) {
      console.error("Error stopping timer:", error);
      showError("Failed to stop timer: " + (error.response?.data?.error || error.message));
    }
  }
  function startTimerPolling() {
    if (state.timerInterval) clearInterval(state.timerInterval);
    state.timerInterval = setInterval(async () => {
      if (!state.apiClient || !state.isTimerRunning) return;
      try {
        const response = await state.apiClient.getTimerStatus();
        if (response.data.active) {
          updateTimerDisplay(response.data.timer);
        } else {
          state.isTimerRunning = false;
          stopTimerPolling();
        }
      } catch (error) {
        console.error("Error polling timer:", error);
      }
    }, 5e3);
  }
  function stopTimerPolling() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
  }
  function updateTimerDisplay(timer) {
    if (!timer) {
      if (window.electronAPI && window.electronAPI.sendTimerStatus) {
        window.electronAPI.sendTimerStatus({ active: false });
      }
      return;
    }
    const startTime = new Date(timer.start_time);
    const now = /* @__PURE__ */ new Date();
    const seconds = Math.floor((now - startTime) / 1e3);
    document.getElementById("timer-display").textContent = formatDurationLong(seconds);
    document.getElementById("timer-project").textContent = timer.project?.name || "Unknown Project";
    const taskEl = document.getElementById("timer-task");
    if (timer.task) {
      taskEl.textContent = timer.task.name;
      taskEl.style.display = "block";
    } else {
      taskEl.style.display = "none";
    }
    const notesEl = document.getElementById("timer-notes");
    if (timer.notes) {
      notesEl.textContent = timer.notes;
      notesEl.style.display = "block";
    } else {
      notesEl.style.display = "none";
    }
    if (window.electronAPI && window.electronAPI.sendTimerStatus) {
      window.electronAPI.sendTimerStatus({ active: true, timer });
    }
  }
  async function loadInvoices() {
    if (!state.apiClient) return;
    try {
      const response = await state.apiClient.getInvoices({
        page: state.pagination.invoices.page,
        perPage: state.pagination.invoices.perPage
      });
      state.cachedInvoices = response.data.invoices || [];
      state.viewLimits.invoices = 20;
      const pagination = response.data.pagination || {};
      state.pagination.invoices.totalPages = Number(pagination.pages || pagination.total_pages || 1) || 1;
      state.pagination.invoices.total = Number(pagination.total || state.cachedInvoices.length) || state.cachedInvoices.length;
      renderInvoices();
      renderInvoicePager();
    } catch (error) {
      console.error("Error loading invoices:", error);
      showError("Failed to load invoices: " + (error.response?.data?.error || error.message));
    }
  }
  function renderInvoicePager() {
    const indicator = document.getElementById("invoice-page-indicator");
    const prevBtn = document.getElementById("invoice-prev-page-btn");
    const nextBtn = document.getElementById("invoice-next-page-btn");
    if (indicator) {
      indicator.textContent = `Page ${state.pagination.invoices.page}/${state.pagination.invoices.totalPages}`;
    }
    if (prevBtn) {
      prevBtn.disabled = state.pagination.invoices.page <= 1;
    }
    if (nextBtn) {
      nextBtn.disabled = state.pagination.invoices.page >= state.pagination.invoices.totalPages;
    }
  }
  async function changeInvoicePage(delta) {
    const nextPage = state.pagination.invoices.page + delta;
    if (nextPage < 1 || nextPage > state.pagination.invoices.totalPages) {
      return;
    }
    state.pagination.invoices.page = nextPage;
    await loadInvoices();
  }
  function renderInvoices() {
    const list = document.getElementById("invoices-list");
    if (!list) return;
    const filtered = state.cachedInvoices.filter((invoice) => {
      const q = state.viewFilters.invoiceQuery;
      if (!q) return true;
      const haystack = `${invoice.invoice_number || ""} ${invoice.client_name || ""} ${invoice.status || ""}`.toLowerCase();
      return haystack.includes(q);
    });
    if (filtered.length === 0) {
      list.innerHTML = '<p class="empty-state">No invoices</p>';
      return;
    }
    const limited = filtered.slice(0, state.viewLimits.invoices);
    const rowsHtml = limited.map((invoice) => {
      const number = invoice.invoice_number || invoice.id || "N/A";
      const status = invoice.status || "unknown";
      const total = invoice.total_amount ?? invoice.total ?? "-";
      const totalNumber = Number(invoice.total_amount ?? invoice.total ?? 0) || 0;
      return `
      <div class="entry-item">
        <div class="entry-info">
          <h3>Invoice ${number}</h3>
          <p>Status: ${status}</p>
        </div>
        <div class="entry-actions">
          <div class="entry-time">${total}</div>
          <button class="btn btn-sm btn-secondary" onclick="updateInvoiceStatusAction(${invoice.id}, 'sent')">Mark Sent</button>
          <button class="btn btn-sm btn-secondary" onclick="markInvoicePaidAction(${invoice.id}, ${totalNumber})">Mark Paid</button>
          <button class="btn btn-sm btn-danger" onclick="updateInvoiceStatusAction(${invoice.id}, 'cancelled')">Cancel</button>
        </div>
      </div>
    `;
    }).join("");
    const hasMore = filtered.length > limited.length;
    list.innerHTML = rowsHtml + (hasMore ? `<div style="padding-top:8px;"><button class="btn btn-secondary" onclick="loadMoreInvoices()">Load More</button></div>` : "");
  }
  async function loadExpenses() {
    if (!state.apiClient) return;
    try {
      const response = await state.apiClient.getExpenses({
        page: state.pagination.expenses.page,
        perPage: state.pagination.expenses.perPage
      });
      state.cachedExpenses = response.data.expenses || [];
      state.viewLimits.expenses = 20;
      const pagination = response.data.pagination || {};
      state.pagination.expenses.totalPages = Number(pagination.pages || pagination.total_pages || 1) || 1;
      state.pagination.expenses.total = Number(pagination.total || state.cachedExpenses.length) || state.cachedExpenses.length;
      renderExpenses();
      renderExpensePager();
    } catch (error) {
      console.error("Error loading expenses:", error);
      showError("Failed to load expenses: " + (error.response?.data?.error || error.message));
    }
  }
  function renderExpensePager() {
    const indicator = document.getElementById("expense-page-indicator");
    const prevBtn = document.getElementById("expense-prev-page-btn");
    const nextBtn = document.getElementById("expense-next-page-btn");
    if (indicator) {
      indicator.textContent = `Page ${state.pagination.expenses.page}/${state.pagination.expenses.totalPages}`;
    }
    if (prevBtn) {
      prevBtn.disabled = state.pagination.expenses.page <= 1;
    }
    if (nextBtn) {
      nextBtn.disabled = state.pagination.expenses.page >= state.pagination.expenses.totalPages;
    }
  }
  async function changeExpensePage(delta) {
    const nextPage = state.pagination.expenses.page + delta;
    if (nextPage < 1 || nextPage > state.pagination.expenses.totalPages) {
      return;
    }
    state.pagination.expenses.page = nextPage;
    await loadExpenses();
  }
  function renderExpenses() {
    const list = document.getElementById("expenses-list");
    if (!list) return;
    const filtered = state.cachedExpenses.filter((expense) => {
      const q = state.viewFilters.expenseQuery;
      if (!q) return true;
      const haystack = `${expense.title || ""} ${expense.category || ""} ${expense.expense_date || ""}`.toLowerCase();
      return haystack.includes(q);
    });
    if (filtered.length === 0) {
      list.innerHTML = '<p class="empty-state">No expenses</p>';
      return;
    }
    const limited = filtered.slice(0, state.viewLimits.expenses);
    const rowsHtml = limited.map((expense) => {
      const category = expense.category || "General";
      const amount = expense.amount ?? "-";
      const date = expense.expense_date || expense.date || "";
      return `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${category}</h3>
          <p>${date}</p>
        </div>
        <div class="entry-time">${amount}</div>
      </div>
    `;
    }).join("");
    const hasMore = filtered.length > limited.length;
    list.innerHTML = rowsHtml + (hasMore ? `<div style="padding-top:8px;"><button class="btn btn-secondary" onclick="loadMoreExpenses()">Load More</button></div>` : "");
  }
  async function loadWorkforce() {
    if (!state.apiClient) return;
    try {
      const start = /* @__PURE__ */ new Date();
      start.setDate(start.getDate() - start.getDay() + 1);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      const startDate = start.toISOString().split("T")[0];
      const endDate = end.toISOString().split("T")[0];
      const [periodsResponse, capacityResponse, requestsResponse, balancesResponse] = await Promise.all([
        state.apiClient.getTimesheetPeriods({ startDate, endDate }),
        state.apiClient.getCapacityReport({ startDate, endDate }),
        state.apiClient.getTimeOffRequests({}),
        state.apiClient.getTimeOffBalances({})
      ]);
      state.cachedWorkforce = {
        periods: periodsResponse.data.timesheet_periods || [],
        capacity: capacityResponse.data.capacity || [],
        timeOffRequests: requestsResponse.data.time_off_requests || [],
        balances: balancesResponse.data.balances || []
      };
      state.viewLimits.timeoff = 20;
      renderWorkforce();
    } catch (error) {
      console.error("Error loading workforce view:", error);
      showError("Failed to load workforce data: " + (error.response?.data?.error || error.message));
    }
  }
  function renderWorkforce() {
    renderPeriods();
    renderCapacity();
    renderTimeOffRequests();
    renderBalances();
  }
  function renderPeriods() {
    const periods = state.cachedWorkforce.periods || [];
    const periodsList = document.getElementById("periods-list");
    if (!periodsList) return;
    if (periods.length === 0) {
      periodsList.innerHTML = '<p class="empty-state">No periods</p>';
      return;
    }
    periodsList.innerHTML = periods.map((period) => `
    <div class="entry-item">
      <div class="entry-info">
        <h3>${period.period_start} - ${period.period_end}</h3>
        <p>Status: ${period.status}</p>
      </div>
      <div class="entry-actions">
        ${String(period.status || "").toLowerCase() === "draft" ? `<button class="btn btn-sm btn-primary" onclick="submitTimesheetPeriodAction(${period.id})">Submit</button>` : ""}
        ${String(period.status || "").toLowerCase() === "submitted" && currentUserProfile.can_approve ? `<button class="btn btn-sm btn-primary" onclick="reviewTimesheetPeriodAction(${period.id}, true)">Approve</button>` : ""}
        ${String(period.status || "").toLowerCase() === "submitted" && currentUserProfile.can_approve ? `<button class="btn btn-sm btn-danger" onclick="reviewTimesheetPeriodAction(${period.id}, false)">Reject</button>` : ""}
      </div>
    </div>
  `).join("");
  }
  function renderCapacity() {
    const capacity = state.cachedWorkforce.capacity || [];
    const capacityList = document.getElementById("capacity-list");
    if (!capacityList) return;
    if (capacity.length === 0) {
      capacityList.innerHTML = '<p class="empty-state">No capacity rows</p>';
      return;
    }
    capacityList.innerHTML = capacity.map((row) => {
      const username = row.username || row.user_id || "User";
      const expected = row.expected_hours ?? 0;
      const allocated = row.allocated_hours ?? 0;
      const util = row.utilization_pct ?? 0;
      return `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${username}</h3>
          <p>Expected ${expected}h | Allocated ${allocated}h</p>
        </div>
        <div class="entry-time">${util}%</div>
      </div>
    `;
    }).join("");
  }
  function renderTimeOffRequests() {
    const requests = state.cachedWorkforce.timeOffRequests || [];
    const timeoffList = document.getElementById("timeoff-list");
    if (!timeoffList) return;
    const filtered = requests.filter((req) => {
      const q = state.viewFilters.timeoffQuery;
      if (!q) return true;
      const haystack = `${req.leave_type_name || ""} ${req.status || ""} ${req.start_date || ""} ${req.end_date || ""}`.toLowerCase();
      return haystack.includes(q);
    });
    if (filtered.length === 0) {
      timeoffList.innerHTML = '<p class="empty-state">No time-off requests</p>';
      return;
    }
    const limited = filtered.slice(0, state.viewLimits.timeoff);
    const rowsHtml = limited.map((req) => {
      const leaveType = req.leave_type_name || "Leave";
      const status = req.status || "";
      const pending = String(status).toLowerCase() === "submitted";
      const canReview = pending && currentUserProfile.can_approve;
      return `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${leaveType}</h3>
          <p>${req.start_date} - ${req.end_date}</p>
        </div>
        <div class="entry-actions">
          <div class="entry-time">${status}</div>
          ${canReview ? `<button class="btn btn-sm btn-primary" onclick="reviewTimeOffRequestAction(${req.id}, true)">Approve</button>` : ""}
          ${canReview ? `<button class="btn btn-sm btn-danger" onclick="reviewTimeOffRequestAction(${req.id}, false)">Reject</button>` : ""}
        </div>
      </div>
    `;
    }).join("");
    const hasMore = filtered.length > limited.length;
    timeoffList.innerHTML = rowsHtml + (hasMore ? `<div style="padding-top:8px;"><button class="btn btn-secondary" onclick="loadMoreTimeOffRequests()">Load More</button></div>` : "");
  }
  function renderBalances() {
    const balances = state.cachedWorkforce.balances || [];
    const balancesList = document.getElementById("balances-list");
    if (!balancesList) return;
    if (balances.length === 0) {
      balancesList.innerHTML = '<p class="empty-state">No leave balances</p>';
      return;
    }
    balancesList.innerHTML = balances.map((bal) => {
      const leaveType = bal.leave_type_name || "Leave";
      const remaining = bal.remaining_hours ?? bal.balance_hours ?? 0;
      return `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${leaveType}</h3>
        </div>
        <div class="entry-time">${remaining}h</div>
      </div>
    `;
    }).join("");
  }
  async function showCreateInvoiceDialog() {
    if (!state.apiClient) return;
    try {
      const [projectsResponse, clientsResponse] = await Promise.all([
        state.apiClient.getProjects({ status: "active", perPage: 100 }),
        state.apiClient.getClients({ status: "active", perPage: 100 })
      ]);
      const projects = projectsResponse.data.projects || [];
      const clients = clientsResponse.data.clients || [];
      if (projects.length === 0 || clients.length === 0) {
        showError("Need at least one active project and client to create an invoice");
        return;
      }
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.innerHTML = `
      <div class="modal-content" style="max-width: 560px;">
        <div class="modal-header">
          <h3>Create Invoice</h3>
          <button class="modal-close" onclick="this.closest('.modal').remove()">\xD7</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="invoice-project-select">Project *</label>
            <select id="invoice-project-select" class="form-control">
              ${projects.map((p) => `<option value="${p.id}">${p.name}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label for="invoice-client-select">Client *</label>
            <select id="invoice-client-select" class="form-control">
              ${clients.map((c) => `<option value="${c.id}">${c.name}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label for="invoice-due-date">Due date *</label>
            <input type="date" id="invoice-due-date" class="form-control" value="${new Date(Date.now() + 14 * 24 * 60 * 60 * 1e3).toISOString().split("T")[0]}">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="btn btn-primary" id="invoice-create-btn">Create</button>
        </div>
      </div>
    `;
      document.body.appendChild(modal);
      const createBtn = modal.querySelector("#invoice-create-btn");
      createBtn.addEventListener("click", async () => {
        const projectId = Number(modal.querySelector("#invoice-project-select").value);
        const clientId = Number(modal.querySelector("#invoice-client-select").value);
        const dueDate = modal.querySelector("#invoice-due-date").value;
        const client = clients.find((c) => Number(c.id) === clientId);
        if (!projectId || !clientId || !client || !dueDate) {
          showError("Please provide all required fields");
          return;
        }
        await state.apiClient.createInvoice({
          project_id: projectId,
          client_id: clientId,
          client_name: client.name,
          due_date: dueDate
        });
        modal.remove();
        showSuccess("Invoice created successfully");
        await loadInvoices();
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      });
    } catch (error) {
      showError("Failed to create invoice: " + (error.response?.data?.error || error.message));
    }
  }
  async function showCreateTimeOffDialog() {
    if (!state.apiClient) return;
    try {
      const leaveTypesResponse = await state.apiClient.getLeaveTypes();
      const leaveTypes = leaveTypesResponse.data.leave_types || [];
      if (leaveTypes.length === 0) {
        showError("No leave types available");
        return;
      }
      const modal = document.createElement("div");
      modal.className = "modal";
      const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
      modal.innerHTML = `
      <div class="modal-content" style="max-width: 560px;">
        <div class="modal-header">
          <h3>Create Time-Off Request</h3>
          <button class="modal-close" onclick="this.closest('.modal').remove()">\xD7</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="timeoff-leave-type">Leave type *</label>
            <select id="timeoff-leave-type" class="form-control">
              ${leaveTypes.map((lt) => `<option value="${lt.id}">${lt.name}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label for="timeoff-start-date">Start date *</label>
            <input type="date" id="timeoff-start-date" class="form-control" value="${today}">
          </div>
          <div class="form-group">
            <label for="timeoff-end-date">End date *</label>
            <input type="date" id="timeoff-end-date" class="form-control" value="${today}">
          </div>
          <div class="form-group">
            <label for="timeoff-hours">Requested hours (optional)</label>
            <input type="number" step="0.25" id="timeoff-hours" class="form-control">
          </div>
          <div class="form-group">
            <label for="timeoff-comment">Comment (optional)</label>
            <textarea id="timeoff-comment" class="form-control" rows="2"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="btn btn-primary" id="timeoff-create-btn">Create</button>
        </div>
      </div>
    `;
      document.body.appendChild(modal);
      modal.querySelector("#timeoff-create-btn").addEventListener("click", async () => {
        const leaveTypeId = Number(modal.querySelector("#timeoff-leave-type").value);
        const startDate = modal.querySelector("#timeoff-start-date").value;
        const endDate = modal.querySelector("#timeoff-end-date").value;
        const hoursValue = modal.querySelector("#timeoff-hours").value.trim();
        const requestedHours = hoursValue ? Number(hoursValue) : null;
        const comment = modal.querySelector("#timeoff-comment").value.trim();
        if (!leaveTypeId || !startDate || !endDate) {
          showError("Please provide leave type and dates");
          return;
        }
        if (hoursValue && !Number.isFinite(requestedHours)) {
          showError("requested_hours must be numeric");
          return;
        }
        await state.apiClient.createTimeOffRequest({
          leaveTypeId,
          startDate,
          endDate,
          requestedHours,
          comment,
          submit: true
        });
        modal.remove();
        showSuccess("Time-off request created");
        await loadWorkforce();
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      });
    } catch (error) {
      showError("Failed to create time-off request: " + (error.response?.data?.error || error.message));
    }
  }
  async function showCreateExpenseDialog() {
    if (!state.apiClient) return;
    try {
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.innerHTML = `
      <div class="modal-content" style="max-width: 560px;">
        <div class="modal-header">
          <h3>Create Expense</h3>
          <button class="modal-close" onclick="this.closest('.modal').remove()">\xD7</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="expense-title">Title *</label>
            <input type="text" id="expense-title" class="form-control" placeholder="Taxi to client office">
          </div>
          <div class="form-group">
            <label for="expense-category">Category *</label>
            <input type="text" id="expense-category" class="form-control" value="travel">
          </div>
          <div class="form-group">
            <label for="expense-amount">Amount *</label>
            <input type="number" step="0.01" id="expense-amount" class="form-control">
          </div>
          <div class="form-group">
            <label for="expense-date">Expense date *</label>
            <input type="date" id="expense-date" class="form-control" value="${(/* @__PURE__ */ new Date()).toISOString().split("T")[0]}">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="btn btn-primary" id="expense-create-btn">Create</button>
        </div>
      </div>
    `;
      document.body.appendChild(modal);
      modal.querySelector("#expense-create-btn").addEventListener("click", async () => {
        const title = modal.querySelector("#expense-title").value.trim();
        const category = modal.querySelector("#expense-category").value.trim();
        const amount = Number(modal.querySelector("#expense-amount").value);
        const expenseDate = modal.querySelector("#expense-date").value;
        if (!title || !category || !expenseDate || !Number.isFinite(amount) || amount <= 0) {
          showError("Please provide valid title/category/amount/date");
          return;
        }
        await state.apiClient.createExpense({
          title,
          category,
          amount,
          expense_date: expenseDate
        });
        modal.remove();
        showSuccess("Expense created successfully");
        await loadExpenses();
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      });
    } catch (error) {
      showError("Failed to create expense: " + (error.response?.data?.error || error.message));
    }
  }
  async function loadSettings() {
    const serverUrl = await storeGet("server_url") || "";
    const apiToken = await storeGet("api_token") || "";
    const autoSync = await storeGet("auto_sync");
    const syncInterval = await storeGet("sync_interval");
    const serverUrlInput = document.getElementById("settings-server-url");
    const apiTokenInput = document.getElementById("settings-api-token");
    const autoSyncInput = document.getElementById("auto-sync");
    const syncIntervalInput = document.getElementById("sync-interval");
    if (serverUrlInput) {
      serverUrlInput.value = serverUrl;
    }
    if (apiTokenInput) {
      apiTokenInput.value = apiToken ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" : "";
      apiTokenInput.dataset.hasToken = apiToken ? "true" : "false";
    }
    if (autoSyncInput) {
      autoSyncInput.checked = autoSync !== null ? Boolean(autoSync) : true;
    }
    if (syncIntervalInput) {
      syncIntervalInput.value = (syncInterval || 60).toString();
    }
    updateSyncIntervalState();
  }
  function updateSyncIntervalState() {
    const autoSyncInput = document.getElementById("auto-sync");
    const syncIntervalInput = document.getElementById("sync-interval");
    if (!autoSyncInput || !syncIntervalInput) return;
    syncIntervalInput.disabled = !autoSyncInput.checked;
  }
  async function handleSaveSettings() {
    const serverUrlInput = document.getElementById("settings-server-url");
    const apiTokenInput = document.getElementById("settings-api-token");
    const autoSyncInput = document.getElementById("auto-sync");
    const syncIntervalInput = document.getElementById("sync-interval");
    const messageDiv = document.getElementById("settings-message");
    if (!serverUrlInput || !apiTokenInput || !autoSyncInput || !syncIntervalInput) return;
    const serverUrl = serverUrlInput.value.trim();
    const apiToken = apiTokenInput.value.trim();
    const autoSync = autoSyncInput.checked;
    const syncInterval = parseInt(syncIntervalInput.value, 10);
    if (!serverUrl || !isValidUrl(serverUrl)) {
      showSettingsMessage("Please enter a valid server URL", "error");
      return;
    }
    const hasExistingToken = apiTokenInput.dataset.hasToken === "true";
    let finalApiToken = apiToken;
    if (hasExistingToken && apiToken === "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022") {
      finalApiToken = await storeGet("api_token");
    } else if (!apiToken || !apiToken.startsWith("tt_")) {
      showSettingsMessage("Please enter a valid API token (must start with tt_)", "error");
      return;
    }
    if (Number.isNaN(syncInterval) || syncInterval < 10) {
      showSettingsMessage("Sync interval must be at least 10 seconds", "error");
      return;
    }
    try {
      await storeSet("server_url", serverUrl);
      await storeSet("api_token", finalApiToken);
      await storeSet("auto_sync", autoSync);
      await storeSet("sync_interval", syncInterval);
      state.apiClient = new ApiClient(serverUrl);
      await state.apiClient.setAuthToken(finalApiToken);
      const isValid = await state.apiClient.validateToken();
      if (isValid) {
        await loadCurrentUserProfile();
        updateConnectionStatus("connected");
        showSettingsMessage("Settings saved successfully!", "success");
        apiTokenInput.value = "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022";
        apiTokenInput.dataset.hasToken = "true";
      } else {
        updateConnectionStatus("error");
        showSettingsMessage("Settings saved, but connection test failed. Please check your API token.", "warning");
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      showSettingsMessage("Error saving settings: " + error.message, "error");
    }
  }
  async function handleTestConnection() {
    const serverUrlInput = document.getElementById("settings-server-url");
    const apiTokenInput = document.getElementById("settings-api-token");
    const messageDiv = document.getElementById("settings-message");
    if (!serverUrlInput || !apiTokenInput) return;
    const serverUrl = serverUrlInput.value.trim();
    let apiToken = apiTokenInput.value.trim();
    if (!serverUrl || !isValidUrl(serverUrl)) {
      showSettingsMessage("Please enter a valid server URL", "error");
      return;
    }
    const hasExistingToken = apiTokenInput.dataset.hasToken === "true";
    if (hasExistingToken && apiToken === "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022") {
      apiToken = await storeGet("api_token");
    }
    if (!apiToken || !apiToken.startsWith("tt_")) {
      showSettingsMessage("Please enter a valid API token (must start with tt_)", "error");
      return;
    }
    try {
      showSettingsMessage("Testing connection...", "info");
      const testClient = new ApiClient(serverUrl);
      await testClient.setAuthToken(apiToken);
      const isValid = await testClient.validateToken();
      if (isValid) {
        updateConnectionStatus("connected");
        showSettingsMessage("Connection successful!", "success");
      } else {
        updateConnectionStatus("error");
        showSettingsMessage("Connection failed. Please check your server URL and API token.", "error");
      }
    } catch (error) {
      console.error("Error testing connection:", error);
      showSettingsMessage("Connection error: " + error.message, "error");
    }
  }
  function showSettingsMessage(message, type2 = "info") {
    const messageDiv = document.getElementById("settings-message");
    if (!messageDiv) return;
    messageDiv.textContent = message;
    messageDiv.className = `message message-${type2}`;
    messageDiv.style.display = "block";
    if (type2 === "success" || type2 === "info") {
      setTimeout(() => {
        messageDiv.style.display = "none";
      }, 5e3);
    }
  }
  async function handleLogout() {
    if (confirm("Are you sure you want to logout?")) {
      await storeClear();
      state.apiClient = null;
      state.isTimerRunning = false;
      stopTimerPolling();
      showLoginScreen();
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
  } else {
    initApp();
  }
  var { formatDuration, formatDurationLong, formatDateTime, isValidUrl } = window.Helpers || {};
  function toggleFilters() {
    const filtersEl = document.getElementById("entries-filters");
    if (filtersEl) {
      filtersEl.style.display = filtersEl.style.display === "none" ? "block" : "none";
    }
  }
  async function applyFilters() {
    const startDate = document.getElementById("filter-start-date")?.value || null;
    const endDate = document.getElementById("filter-end-date")?.value || null;
    const projectId = document.getElementById("filter-project")?.value ? parseInt(document.getElementById("filter-project").value) : null;
    currentFilters = { startDate, endDate, projectId };
    await loadTimeEntries();
  }
  function clearFilters() {
    currentFilters = { startDate: null, endDate: null, projectId: null };
    document.getElementById("filter-start-date").value = "";
    document.getElementById("filter-end-date").value = "";
    document.getElementById("filter-project").value = "";
    loadTimeEntries();
  }
  async function loadProjectsForFilter() {
    if (!state.apiClient) return;
    try {
      const response = await state.apiClient.getProjects({ status: "active" });
      const projects = response.data.projects || [];
      const select = document.getElementById("filter-project");
      if (select) {
        select.innerHTML = '<option value="">All Projects</option>' + projects.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
        if (currentFilters.projectId) {
          select.value = String(currentFilters.projectId);
        }
      }
    } catch (error) {
      console.error("Error loading projects for filter:", error);
    }
  }
  async function showTimeEntryForm(entryId = null) {
    let projects = [];
    let requirements = { require_task: false, require_description: false, description_min_length: 20 };
    try {
      const [projectsResponse, usersMeResponse] = await Promise.all([
        state.apiClient.getProjects({ status: "active" }),
        state.apiClient.getUsersMe().catch(() => ({}))
      ]);
      projects = projectsResponse.data.projects || [];
      if (usersMeResponse.time_entry_requirements) {
        requirements = usersMeResponse.time_entry_requirements;
      }
    } catch (error) {
      showError("Failed to load projects");
      return;
    }
    let entry = null;
    if (entryId) {
      try {
        const entryResponse = await state.apiClient.getTimeEntry(entryId);
        entry = entryResponse.data.time_entry;
      } catch (error) {
        showError("Failed to load time entry");
        return;
      }
    }
    let tasks = [];
    const projectId = entry ? entry.project_id : null;
    if (projectId) {
      try {
        const tasksResponse = await state.apiClient.getTasks({ projectId });
        tasks = tasksResponse.data.tasks || [];
      } catch (error) {
        console.error("Failed to load tasks:", error);
      }
    }
    const modal = document.createElement("div");
    modal.className = "modal";
    const startDate = entry ? new Date(entry.start_time).toISOString().split("T")[0] : (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
    const startTime = entry ? new Date(entry.start_time).toTimeString().slice(0, 5) : (/* @__PURE__ */ new Date()).toTimeString().slice(0, 5);
    const endDate = entry && entry.end_time ? new Date(entry.end_time).toISOString().split("T")[0] : "";
    const endTime = entry && entry.end_time ? new Date(entry.end_time).toTimeString().slice(0, 5) : "";
    modal.innerHTML = `
    <div class="modal-content" style="max-width: 600px;">
      <div class="modal-header">
        <h3>${entryId ? "Edit" : "Add"} Time Entry</h3>
        <button class="modal-close" onclick="this.closest('.modal').remove()">\xD7</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label for="entry-project-select">Project *</label>
          <select id="entry-project-select" class="form-control" required>
            <option value="">Select a project...</option>
            ${projects.map((p) => `<option value="${p.id}" ${entry && entry.project_id === p.id ? "selected" : ""}>${p.name}</option>`).join("")}
          </select>
        </div>
        <div class="form-group">
          <label for="entry-task-select">${requirements.require_task ? "Task *" : "Task (Optional)"}</label>
          <select id="entry-task-select" class="form-control">
            <option value="">No task</option>
            ${tasks.map((t) => `<option value="${t.id}" ${entry && entry.task_id === t.id ? "selected" : ""}>${t.name}</option>`).join("")}
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="entry-start-date">Start Date *</label>
            <input type="date" id="entry-start-date" class="form-control" value="${startDate}" required>
          </div>
          <div class="form-group">
            <label for="entry-start-time">Start Time *</label>
            <input type="time" id="entry-start-time" class="form-control" value="${startTime}" required>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="entry-end-date">End Date (Optional)</label>
            <input type="date" id="entry-end-date" class="form-control" value="${endDate}">
          </div>
          <div class="form-group">
            <label for="entry-end-time">End Time (Optional)</label>
            <input type="time" id="entry-end-time" class="form-control" value="${endTime}">
          </div>
        </div>
        <div class="form-group">
          <label for="entry-notes">${requirements.require_description ? "Notes *" : "Notes"}</label>
          <textarea id="entry-notes" class="form-control" rows="3">${entry?.notes || ""}</textarea>
        </div>
        <div class="form-group">
          <label for="entry-tags">Tags (comma-separated)</label>
          <input type="text" id="entry-tags" class="form-control" value="${entry?.tags || ""}">
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" id="entry-billable" ${entry ? entry.billable ? "checked" : "" : "checked"}>
            Billable
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
        <button class="btn btn-primary" id="save-entry-btn">${entryId ? "Update" : "Create"}</button>
      </div>
    </div>
  `;
    document.body.appendChild(modal);
    const projectSelect = modal.querySelector("#entry-project-select");
    const taskSelect = modal.querySelector("#entry-task-select");
    const saveBtn = modal.querySelector("#save-entry-btn");
    projectSelect.addEventListener("change", async (e) => {
      const projectId2 = parseInt(e.target.value);
      if (!projectId2) {
        taskSelect.innerHTML = '<option value="">No task</option>';
        return;
      }
      try {
        const tasksResponse = await state.apiClient.getTasks({ projectId: projectId2 });
        const tasks2 = tasksResponse.data.tasks || [];
        taskSelect.innerHTML = '<option value="">No task</option>' + tasks2.map((t) => `<option value="${t.id}">${t.name}</option>`).join("");
      } catch (error) {
        console.error("Failed to load tasks:", error);
      }
    });
    saveBtn.addEventListener("click", async () => {
      const projectId2 = parseInt(projectSelect.value);
      if (!projectId2) {
        showError("Please select a project");
        return;
      }
      const taskId = taskSelect.value ? parseInt(taskSelect.value) : null;
      if (requirements.require_task && !taskId) {
        showError("A task must be selected when logging time for a project");
        return;
      }
      const notesEl = document.getElementById("entry-notes");
      const notes = notesEl ? notesEl.value.trim() : "";
      if (requirements.require_description) {
        if (!notes) {
          showError("A description is required when logging time");
          return;
        }
        const minLen = requirements.description_min_length || 20;
        if (notes.length < minLen) {
          showError(`Description must be at least ${minLen} characters`);
          return;
        }
      }
      const startDate2 = document.getElementById("entry-start-date").value;
      const startTime2 = document.getElementById("entry-start-time").value;
      const endDate2 = document.getElementById("entry-end-date").value;
      const endTime2 = document.getElementById("entry-end-time").value;
      const notesForApi = notes || null;
      const tags = document.getElementById("entry-tags").value.trim() || null;
      const billable = document.getElementById("entry-billable").checked;
      const startDateTime = (/* @__PURE__ */ new Date(`${startDate2}T${startTime2}`)).toISOString();
      const endDateTime = endDate2 && endTime2 ? (/* @__PURE__ */ new Date(`${endDate2}T${endTime2}`)).toISOString() : null;
      try {
        if (entryId) {
          await state.apiClient.updateTimeEntry(entryId, {
            project_id: projectId2,
            task_id: taskId,
            start_time: startDateTime,
            end_time: endDateTime,
            notes: notesForApi,
            tags,
            billable
          });
          showSuccess("Time entry updated successfully");
        } else {
          await state.apiClient.createTimeEntry({
            project_id: projectId2,
            task_id: taskId,
            start_time: startDateTime,
            end_time: endDateTime,
            notes: notesForApi,
            tags,
            billable
          });
          showSuccess("Time entry created successfully");
        }
        modal.remove();
        loadTimeEntries();
      } catch (error) {
        showError("Failed to save time entry: " + (error.response?.data?.error || error.message));
      }
    });
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }
})();
/*! Bundled license information:

axios/dist/browser/axios.cjs:
  (*! Axios v1.13.2 Copyright (c) 2025 Matt Zabriskie and contributors *)
*/
