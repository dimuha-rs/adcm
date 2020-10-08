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
import { Component, ElementRef, OnInit } from '@angular/core';
import { AppService } from '@app/core';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  template: `
    <app-top></app-top>
    <app-tooltip></app-tooltip>
    <main>
      <app-progress></app-progress>
      <router-outlet></router-outlet>
    </main>
    <footer>
      <div>
        <span class="left">
          <span>VERSION: </span>
          <a target="_blank" rel="noopener" href="https://docs.arenadata.io/adcm/notes.html#{{ versionData.version }}">{{ versionData.version }}-{{ versionData.commit_id }}</a>
        </span>
        <span>ARENADATA &copy; {{ currentYear }}</span>
      </div>
    </footer>
    <div class="console hidden"></div>
  `,
  providers: [AppService],
})
export class AppComponent implements OnInit {
  currentYear = new Date().getFullYear();
  versionData = { version: '', commit_id: '' };

  constructor(private elRef: ElementRef, private service: AppService) {}

  ngOnInit(): void {
    this.service.getRootAndCheckAuth().subscribe((c) => {
      if (!c) {
        this.elRef.nativeElement.innerHTML = '';
      } else {
        this.versionData = { ...c };
      }
    });

    this.service.initListeners();

    this.service
      .checkWSconnectStatus()
      .pipe(filter((a) => a === 'open'))
      .subscribe((_) => this.console('Socket status :: open', 'socket'));

    this.service.checkUserProfile().subscribe((_) => this.console('User profile :: saved', 'profile'));

    this.versionData = this.service.getVersion(this.versionData);
  }

  console(text: string, css?: string): void {
    const console = this.elRef.nativeElement.querySelector('div.console');
    if (!text) {
      console.innerHTML = '';
    }
    else {
      const create = () => document.createElement('p');
      const isExist = () => console.querySelector(`.${css}`);
      const inner = (p: HTMLElement) => (p.innerText = text);
      const addClass = (p: HTMLElement) => p.classList.add(css);
      const append = (p: HTMLElement) => console.appendChild(p);
      const a = create();
      inner(a);
      if (css && !isExist()) {
        addClass(a);
        append(a);
      }
    }
  }
}
