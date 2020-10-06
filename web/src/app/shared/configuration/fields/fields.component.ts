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
import { Component, EventEmitter, Input, Output, QueryList, ViewChildren } from '@angular/core';

import { FieldService } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { FieldOptions, IConfig, PanelOptions } from '../types';

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let item of dataOptions; trackBy: trackBy">
      <app-group-fields *ngIf="isPanel(item); else one" [panel]="item" [form]="form"></app-group-fields>
      <ng-template #one>
        <app-field *ngIf="!item.hidden" [form]="form" [options]="item" [ngClass]="{ 'read-only': item.read_only }"></app-field>
      </ng-template>
    </ng-container>
  `,
})
export class ConfigFieldsComponent {
  @Input() dataOptions: (FieldOptions | PanelOptions)[] = [];
  @Input() form = this.service.toFormGroup();
  rawConfig: IConfig;
  shapshot: any;
  isAdvanced = false;

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  @Input()
  set model(data: IConfig) {
    if (!data) {
      return;
    }
    this.rawConfig = data;
    this.dataOptions = this.service.getPanels(data);
    this.form = this.service.toFormGroup(this.dataOptions);
    this.isAdvanced = data.config.some((a) => a.ui_options && a.ui_options.advanced);
    this.shapshot = { ...this.form.value };
    this.event.emit({ name: 'load', data: { form: this.form } });
  }

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  constructor(private service: FieldService) {}

  get attr() {
    return this.dataOptions
      .filter((a) => a.type === 'group' && (a as PanelOptions).activatable)
      .reduce((p, c: PanelOptions) => ({ ...p, [c.name]: { active: c.active } }), {});
  }

  isPanel(item: FieldOptions | PanelOptions): boolean {
    return 'options' in item && !item.hidden;
  }

  trackBy(index: number, item: PanelOptions): string {
    return item.name;
  }
}
