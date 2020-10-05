// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Injectable } from '@angular/core';
import { getControlType, getPattern, IRoot } from '@app/core/types';

import { FieldOptions, controlType, ValidatorInfo } from '../types';

export type simpleType = 'string' | 'integer' | 'float' | 'bool' | 'int' | 'one_of' | 'dict_key_selection';
export type reqursionType = 'list' | 'dict';
export type matchType = simpleType | reqursionType;

interface IYRoot {
  match: matchType;
  selector?: string;
  variants?: { [key: string]: string };
  item?: string;
  items?: IRoot;
  required_items?: string[];
  default_item?: string;
}

export interface IYspec {
  [key: string]: IYRoot;
}

/**
 *```
{
    name:         string;
    path:         string[];
    type:         simpleType;
    controlType:  controlType;
    validator:    ValidatorInfo;
}
 *```
 */
export interface IYField {
  name: string;
  path: string[];
  type: simpleType;
  controlType: controlType;
  validator: ValidatorInfo;
}

/**
 * ```
 * {
 *   name:      string;
 *   type:      reqursionType;    // 'list' | 'dict'
 *   options:   IYContainer | IYField | (IYContainer | IYField)[];
 * }
 *```
 */
export interface IYContainer {
  name: string;
  type: reqursionType;
  options: IYContainer | IYField | (IYContainer | IYField)[];
}

export interface IStructure extends FieldOptions {
  rules: { options: any; type: string; name: string };
}

@Injectable()
export class YspecService {
  private root: IYspec;

  set Root(yspec: IYspec) {
    this.root = yspec;
  }

  get Root() {
    return this.root;
  }

  build(rule = 'root', path: string[] = []): IYContainer | IYField {
    const { match, item, items } = this.Root[rule];

    switch (match) {
      case 'list':
        return this.list(item, path);
      case 'dict':
        return this.dict(items, path);
      // case 'one_of':
      //   return this.one_of();
      // case 'dict_key_selection':
      //   return this.dict_key_selection();
      default:
        return this.field({ type: match, path });
    }
  }

  field(field: { type: simpleType; path: string[] }): IYField {
    const name = field.path.reverse()[0];
    return {
      name,
      type: field.type,
      path: field.path,
      controlType: getControlType(field.type),
      validator: {
        required: this.findRule(field.path, 'required_items'),
        pattern: getPattern(field.type)
      }
    };
  }

  findRule(path: string[], name: string): boolean {
    const [field, parent] = path;
    const rule = this.Root[parent];
    return !!(rule && rule[name] && Array.isArray(rule[name]) && rule[name].includes(field));
  }

  list(item: string, path: string[]): IYContainer {
    const name = [...path].reverse()[0] || 'root';
    return { type: 'list', name, options: this.build(item, [...path, item]) };
  }

  dict(items: IRoot, path: string[]): IYContainer {
    const name = [...path].reverse()[0] || 'root';
    return {
      type: 'dict',
      name,
      options: Object.keys(items).map((item_name: string) => this.build(items[item_name], [...path, item_name]))
    };
  }

  one_of() {}

  dict_key_selection() {}
}
