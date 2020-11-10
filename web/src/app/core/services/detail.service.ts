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
import { ParamMap } from '@angular/router';
import { ApiService } from '@app/core/api';
import { Bundle, Cluster, Entities, Host, IAction, IImport, Job, LogFile, Provider, Service, TypeName } from '@app/core/types';
import { environment } from '@env/environment';
import { BehaviorSubject, EMPTY, forkJoin, Observable, of } from 'rxjs';
import { filter, map, switchMap, tap } from 'rxjs/operators';

const EntitiNames: TypeName[] = ['host', 'service', 'cluster', 'provider', 'job', 'task', 'bundle'];

export interface WorkerInstance {
  current: Entities;
  cluster: Cluster | null;
}
type pagesType = 'cluster' | 'host' | 'provider' | 'service' | 'job' | 'bundle';

@Injectable({
  providedIn: 'root',
})
export class ClusterService {
  private worker: WorkerInstance | null;
  private workerSubject = new BehaviorSubject<WorkerInstance>(null);
  public worker$ = this.workerSubject.asObservable();

  private _currentParamMap: { [key in pagesType]: number };

  get Cluster() {
    return this.worker ? this.worker.cluster : null;
  }

  set Cluster(cluster: Cluster) {
    if (cluster) cluster.typeName = 'cluster';
    if (this.worker) this.worker.cluster = cluster;
    else this.worker = { current: cluster, cluster: cluster };
  }

  get Current(): Entities {
    return this.worker ? this.worker.current : null;
  }

  constructor(private api: ApiService) {}

  clearWorker() {
    this.worker = null;
  }

  one_cluster(id: number): Observable<Cluster> {
    return this.Cluster ? of(this.Cluster) : this.api.getOne<Cluster>('cluster', id);
  }

  one_service(id: number): Observable<Service> {
    return this.api.get<Service>(`${this.worker.cluster.service}${id}/`);
  }

  one_host(id: number): Observable<Host> {
    return this.api.getOne<Host>('host', id).pipe(map((host: Host) => ({ ...host, name: host.fqdn })));
  }

  one_provider(id: number): Observable<Provider> {
    return this.api.getOne<Provider>('provider', id);
  }

  one_job(id: number): Observable<Job> {
    return this.api.getOne<Job>('job', id).pipe(
      map((j: Job) => ({
        ...j,
        prototype_name: j.action ? j.action.prototype_name : '',
        prototype_version: j.action ? j.action.prototype_version : '',
        bundle_id: j.action ? j.action.bundle_id : null,
        name: j.action ? `${j.action.display_name}` : 'Object has been deleted',
      }))
    );
  }

  one_bundle(id: number): Observable<Bundle> {
    return this.api.get<Bundle>(`${environment.apiRoot}stack/bundle/${id}/`);
  }

  getContext(param: ParamMap): Observable<WorkerInstance> {
    const typeName = EntitiNames.find((a) => param.keys.some((b) => a === b));
    const id = +param.get(typeName);
    const cluster$ = param.has('cluster') ? this.api.getOne<Cluster>('cluster', +param.get('cluster')) : of(null);

    return cluster$
      .pipe(
        tap((cluster) => (this.Cluster = cluster)),
        switchMap((cluster) => (cluster && typeName !== 'cluster' ? this.api.get<Entities>(`${cluster[typeName]}${id}/`) : this[`one_${typeName}`](id)))
      )
      .pipe(
        map((a: Entities) => {
          a.typeName = typeName;
          this.worker.current = { ...a, name: a.display_name || a.name || (a as Host).fqdn };
          this.workerSubject.next(this.worker);
          return this.worker;
        })
      );
  }

  getLog(url: string): Observable<LogFile> {
    return this.api.get<LogFile>(url);
  }

  getActions(): Observable<IAction[]> {
    return typeof this.worker.current.action === 'string' ? this.api.get<IAction[]>(this.worker.current.action) : of([]);
  }

  getServices(p: ParamMap) {
    return this.api.getList<Service>(this.Cluster.service, p).pipe(
      map((r) => {
        r.results = r.results.map((a) => ({ ...a, cluster: this.Cluster }));
        return r;
      })
    );
  }

  addServices(output: { prototype_id: number }[]) {
    return forkJoin(output.map((o) => this.api.post<Service>(this.Cluster.service, o)));
  }

  getHosts(p: ParamMap) {
    return this.api.getList<Host>(this.Cluster.host, p);
  }

  addHost(host_id: number) {
    return this.api.post(this.Cluster.host, { host_id });
  }

  reset(): Observable<WorkerInstance> {
    if (!this.Current) return EMPTY;
    const typeName = this.Current.typeName;
    return this.api.get<Entities>(this.Current.url).pipe(
      filter((_) => !!this.worker),
      map((a) => {
        if (typeName === 'cluster') this.worker.cluster = { ...(a as Cluster), typeName };
        this.worker.current = { ...a, typeName, name: a.display_name || a.name || (a as Host).fqdn };
        return this.worker;
      })
    );
  }

  getMainInfo() {
    return this.api.get<any>(`${this.Current.config}current/`).pipe(
      map((a: any) => a.config.find((b: { name: string }) => b.name === '__main_info')),
      filter((a) => a),
      map((a) => a.value)
    );
  }

  /**
   * Import / Export data for `Cluster`
   */
  getImportData() {
    return 'imports' in this.Current ? this.api.get<IImport[]>(this.Current.imports) : EMPTY;
  }

  bindImport(bind: any) {
    return 'imports' in this.Current ? this.api.post(this.Current.imports, bind) : EMPTY;
  }

  /**
   * For `Job` and `Task` operating time data
   */
  getOperationTimeData(job: Job) {
    const { start_date, finish_date, status } = job;
    const sdn = Date.parse(start_date),
      fdn = Date.parse(finish_date),
      ttm = fdn - sdn,
      sec = Math.floor(ttm / 1000),
      min = Math.floor(sec / 60),
      time = status !== 'running' ? `${min}m. ${sec - min * 60}s.` : '';
    const a = new Date(sdn);
    const b = new Date(fdn);
    return { start: a.toLocaleTimeString(), end: status !== 'running' ? b.toLocaleTimeString() : '', time };
  }
}
