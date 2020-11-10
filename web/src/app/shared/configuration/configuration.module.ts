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
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatOptionModule } from '@angular/material/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { FormElementsModule } from '../form-elements/form-elements.module';
import { StuffModule } from '../stuff.module';
import { FieldService } from './field.service';
import { FieldComponent } from './field/field.component';
import { ConfigFieldsComponent } from './fields/fields.component';
import { GroupFieldsComponent } from './group-fields/group-fields.component';
import { ConfigComponent } from './main/main.component';
import { ItemComponent } from './scheme/item.component';
import { RootComponent } from './scheme/root.component';
import { SchemeComponent } from './scheme/scheme.component';
import { SchemeService } from './scheme/scheme.service';
import { ColorOptionDirective } from './tools/color-option.directive';
import { HistoryComponent } from './tools/history.component';
import { SearchComponent } from './tools/search.component';
import { ToolsComponent } from './tools/tools.component';
import { YspecService } from './yspec/yspec.service';

const material = [
  MatIconModule,
  MatInputModule,
  MatButtonModule,
  MatSelectModule,
  MatOptionModule,
  MatCheckboxModule,
  MatTooltipModule,
  MatToolbarModule,
  MatFormFieldModule,
  MatExpansionModule,
  MatSlideToggleModule,
  MatListModule,
];

@NgModule({
  declarations: [
    FieldComponent,
    ConfigFieldsComponent,
    GroupFieldsComponent,
    ConfigComponent,
    HistoryComponent,
    SearchComponent,
    ColorOptionDirective,
    ToolsComponent,
    SchemeComponent,
    RootComponent,
    ItemComponent,
  ],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, StuffModule, FormElementsModule, ...material],
  exports: [ConfigComponent, ConfigFieldsComponent],
  providers: [FieldService, YspecService, SchemeService],
})
export class ConfigurationModule {}
