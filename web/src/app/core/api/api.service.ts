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
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ParamMap } from '@angular/router';
import { IRoot, TypeName } from '@app/core/types/api';
import { ListResult } from '@app/shared/components/list/list.component';
import { select, Store } from '@ngrx/store';
import { EMPTY, Observable } from 'rxjs';
import { catchError, filter, switchMap } from 'rxjs/operators';

import { State } from '../store';
import { getRoot } from './api.reducer';

@Injectable()
export class ApiService {
  constructor(private http: HttpClient, private store: Store<State>) {}

  get root(): Observable<IRoot> {
    return this.store.pipe(select(getRoot)).pipe(filter((root) => !!root));
  }

  getPure<T>(typeName: TypeName, params: { [key: string]: string } = {}): Observable<T[]> {
    return this.root.pipe(switchMap((root) => this.get<T[]>(root[typeName], params))).pipe(catchError(() => EMPTY));
  }

  getOne<T>(typeName: TypeName, id: number, params: { [key: string]: string } = {}): Observable<T> {
    return this.root
      .pipe(switchMap((root) => this.get<T>(`${root[typeName]}${id}/`, params)))
      .pipe(catchError(() => EMPTY));
  }

  get<T>(url: string, params: { [key: string]: string } = {}): Observable<T> {
    return this.http.get<T>(url, { params });
  }

  getList<T>(url: string, p: ParamMap): Observable<ListResult<T>> {
    const params = p.keys.reduce((pr, c) => ({ ...pr, [c]: p.get(c) }), {});
    if (p) {
      const limit = p.get('limit') ? +p.get('limit') : +localStorage.getItem('limit');
      const offset = (p.get('page') ? +p.get('page') : 0) * limit;
      params['limit'] = limit.toString();
      params['offset'] = offset.toString();
      params['status'] = p.get('filter') || '';
    }
    return this.get<ListResult<T>>(url, params);
  }

  list<T>(url: string, params: { limit: string; offset: string; ordering?: string } | null): Observable<ListResult<T>> {
    if (!params) {
      params = { limit: localStorage.getItem('limit'), offset: '0' };
    }
    return this.get<ListResult<T>>(url, params);
  }

  post<T>(url: string, item: Object | FormData): Observable<T> {
    return this.http.post<T>(url, item);
  }

  put<T>(url: string, item: any): Observable<T> {
    return this.http.put<T>(url, item).pipe(catchError(() => EMPTY));
  }

  patch<T>(url: string, item: any): Observable<T> {
    return this.http.patch<T>(url, item).pipe(catchError(() => EMPTY));
  }

  delete(url: string): Observable<any> {
    return this.http.delete(url).pipe(catchError(() => EMPTY));
  }
}
