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
import { Directive, Renderer2, Host, OnInit, Output, EventEmitter } from '@angular/core';
import { MatSelect } from '@angular/material/select';

const POINT_WHEN_EMMIT = 100;

@Directive({
  selector: '[appInfinityScroll]',
})
export class InfinityScrollDirective implements OnInit {
  @Output() topScrollPoint = new EventEmitter();

  constructor(private renderer: Renderer2, @Host() private el: MatSelect) {}

  ngOnInit(): void {
    if ('openedChange' in this.el) {
      this.el.openedChange.subscribe((open: boolean) => this.registerPanel(open));
    } else {
      this.renderer.listen(this.el, 'scroll', this.onScrollPanel.bind(this));
    }
  }

  registerPanel(open: boolean): void {
    if (open) {
      const panel = (this.el as MatSelect).panel.nativeElement;
      this.renderer.listen(panel, 'scroll', this.onScrollPanel.bind(this));
    }
  }

  onScrollPanel(event: any): void {
    const target = event.target;

    const height = Array.from<HTMLElement>(target.children).reduce((p, c) => p + c.clientHeight, 0) - target.clientHeight;
    if (target.scrollTop > height - POINT_WHEN_EMMIT) {
      this.topScrollPoint.emit();
    }
  }
}
